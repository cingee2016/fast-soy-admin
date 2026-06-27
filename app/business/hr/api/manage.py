"""
HR 管理接口 — 部门/标签/员工的 CRUD (需要系统权限)。
"""

from fastapi import APIRouter, Request, UploadFile

from app.business.hr.controllers import department_controller, employee_controller, tag_controller
from app.business.hr.dependency import DependHrScope
from app.business.hr.files import save_avatar
from app.business.hr.schemas import (
    DepartmentCreate,
    DepartmentSearch,
    DepartmentUpdate,
    EmployeeCreate,
    EmployeeSearch,
    EmployeeTransition,
    EmployeeUpdate,
    TagCreate,
    TagSearch,
    TagUpdate,
)
from app.business.hr.serializers import employee_record
from app.business.hr.services import build_employee_list_query, create_employee, list_employees_with_relations, transition_employee, update_employee
from app.utils import (
    CRUDRouter,
    SearchFieldConfig,
    SqidPath,
    Success,
    SuccessExtra,
    apply_data_policy,
    assert_object_policy,
    require_buttons,
)

# 部门 / 标签是标准资源，优先用 CRUDRouter；route_key_prefix 与 init_data.py 中的角色授权对应。
dept_crud = CRUDRouter(
    prefix="/departments",
    controller=department_controller,
    create_schema=DepartmentCreate,
    update_schema=DepartmentUpdate,
    list_schema=DepartmentSearch,
    search_fields=SearchFieldConfig(contains_fields=["name", "code"], exact_fields=["status"]),
    summary_prefix="部门",
    soft_delete=True,
    tree_endpoint=True,
    enable_routes={"list", "create", "update", "delete", "batch_delete"},
    route_key_prefix="hr.departments",
    action_dependencies={
        "create": [require_buttons("B_HR_DEPT_CREATE")],
        "update": [require_buttons("B_HR_DEPT_EDIT")],
        "delete": [require_buttons("B_HR_DEPT_DELETE")],
        "batch_delete": [require_buttons("B_HR_DEPT_DELETE")],
    },
)

tag_crud = CRUDRouter(
    prefix="/tags",
    controller=tag_controller,
    create_schema=TagCreate,
    update_schema=TagUpdate,
    list_schema=TagSearch,
    search_fields=SearchFieldConfig(contains_fields=["name"], exact_fields=["category"]),
    summary_prefix="标签",
    enable_routes={"list", "create", "update", "delete", "batch_delete"},
    route_key_prefix="hr.tags",
    action_dependencies={
        "create": [require_buttons("B_HR_TAG_CREATE")],
        "update": [require_buttons("B_HR_TAG_EDIT")],
        "delete": [require_buttons("B_HR_TAG_DELETE")],
        "batch_delete": [require_buttons("B_HR_TAG_DELETE")],
    },
)

# 员工的列表/创建/更新均走自定义逻辑（见下方 router 上的手写路由），
# CRUDRouter 仅生成 GET/DELETE 与 batch_delete；create/update 因未传 schema 不注册。
emp_crud = CRUDRouter(
    prefix="/employees",
    controller=employee_controller,
    list_schema=EmployeeSearch,
    summary_prefix="员工",
    soft_delete=True,
    route_key_prefix="hr.employees",
    action_dependencies={
        "delete": [require_buttons("B_HR_EMP_DELETE")],
        "batch_delete": [require_buttons("B_HR_EMP_DELETE")],
    },
)


@emp_crud.override("get")
async def _get_employee(item_id: SqidPath):
    emp = await employee_controller.get(id=item_id)
    await emp.fetch_related("department", "tags")
    return Success(data=await employee_record(emp, department_name=True, tag_ids=True, tag_names=True))


@emp_crud.override("list")
async def _list_employees(obj_in: EmployeeSearch, request: Request):
    q = build_employee_list_query(obj_in)
    scope_q = await apply_data_policy("hr.employees.read", redis=request.app.state.redis, module="hr")
    total, records = await list_employees_with_relations(obj_in, search=q & scope_q)
    return SuccessExtra(data={"records": records}, total=total, current=obj_in.current, size=obj_in.size)


router = APIRouter(tags=["HR管理"], dependencies=[DependHrScope])


# module.py 会给本 router 统一加 /api/v1/business/hr 前缀，这里保持业务内相对路径。
router.include_router(dept_crud.router)
router.include_router(tag_crud.router)
router.include_router(emp_crud.router)


# ---- 员工创建/更新/状态流转：独立走 service 层，按按钮权限隔离 ----


@router.post(
    "/employees",
    summary="创建员工",
    name="hr.employees.create",
    dependencies=[require_buttons("B_HR_EMP_CREATE")],
)
async def create_emp(emp_in: EmployeeCreate, request: Request):
    """HR 管理员视角：必须指定 department_id；自动创建系统用户。

    部门主管创建下属请走 ``POST /hr/team/employees``。
    """
    return await create_employee(emp_in, request.app.state.redis)


@router.patch(
    "/employees/{emp_id}",
    summary="更新员工",
    name="hr.employees.update",
    dependencies=[require_buttons("B_HR_EMP_EDIT")],
)
async def update_emp(emp_id: SqidPath, emp_in: EmployeeUpdate):
    return await update_employee(emp_id, emp_in)


@router.post(
    "/employees/{emp_id}/transition",
    summary="员工状态流转",
    name="hr.employees.transition",
    dependencies=[require_buttons("B_HR_EMP_TRANSITION")],
)
async def transition_emp(emp_id: SqidPath, body: EmployeeTransition):
    """状态流转: pending → onboarding → active → resigned"""
    return await transition_employee(emp_id, body.to_state)


@router.post(
    "/employees/{emp_id}/avatar",
    summary="上传员工头像",
    name="hr.employees.avatar",
    dependencies=[require_buttons("B_HR_EMP_EDIT")],
)
async def upload_avatar(emp_id: SqidPath, file: UploadFile):
    """上传员工头像图片，保存到 static/avatars/，返回访问 URL。"""
    target = await employee_controller.get(id=emp_id)
    # 文件保存前先校验对象权限，避免无权用户制造无用上传文件。
    await assert_object_policy("hr.employees.update", target, module="hr")
    avatar_url = await save_avatar(file)
    await employee_controller.update(id=emp_id, obj_in={"avatar": avatar_url})
    return Success(msg="头像上传成功", data={"avatarUrl": avatar_url})
