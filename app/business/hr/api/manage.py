"""
HR 管理接口 — 部门/标签/员工的 CRUD (需要系统权限)。
"""

from fastapi import APIRouter, Request

from app.business.hr.controllers import department_controller, employee_controller, skill_controller
from app.business.hr.schemas import (
    DepartmentCreate,
    DepartmentSearch,
    DepartmentUpdate,
    EmployeeCreate,
    EmployeeSearch,
    EmployeeUpdate,
    SkillCreate,
    SkillUpdate,
)
from app.business.hr.services import create_employee, get_department_stats, list_employees_with_relations, update_employee
from app.utils import CTX_USER_ID, CRUDRouter, DependPermission, Fail, SearchFieldConfig, Success, SuccessExtra, has_button_code, is_super_admin

dept_crud = CRUDRouter(
    prefix="/departments",
    controller=department_controller,
    create_schema=DepartmentCreate,
    update_schema=DepartmentUpdate,
    list_schema=DepartmentSearch,
    search_fields=SearchFieldConfig(contains_fields=["name", "code"], exact_fields=["status"]),
    summary_prefix="部门",
    list_method="post",
    batch_delete_method="body",
)

skill_crud = CRUDRouter(
    prefix="/skills",
    controller=skill_controller,
    create_schema=SkillCreate,
    update_schema=SkillUpdate,
    summary_prefix="标签",
    batch_delete_method="body",
)

emp_crud = CRUDRouter(
    prefix="/employees",
    controller=employee_controller,
    summary_prefix="员工",
    exclude_fields=["phone"],
    batch_delete_method="body",
    enable_routes={"get", "delete", "batch_delete"},
)

router = APIRouter(prefix="/hr", tags=["HR管理"], dependencies=[DependPermission])


# 具体路径定义在参数化路由（{item_id}）之前，避免路由冲突
@router.get("/departments/stats", summary="部门统计")
async def dept_stats():
    stats = await get_department_stats()
    return Success(data=stats)


router.include_router(dept_crud.router)
router.include_router(skill_crud.router)
router.include_router(emp_crud.router)


@router.post("/employees/all/", summary="查看员工列表")
async def list_employees(obj_in: EmployeeSearch):
    total, records = await list_employees_with_relations(obj_in)
    return SuccessExtra(data={"records": records}, total=total, current=obj_in.current, size=obj_in.size)


@router.post("/employees", summary="创建员工")
async def create_emp(emp_in: EmployeeCreate, request: Request):
    """
    超管: 需指定 department_id
    主管(B_HR_CREATE): department 自动继承
    共同: 自动创建系统用户(R_USER, must_change_password=True), 密码随机生成返回前端
    """
    if not is_super_admin() and not has_button_code("B_HR_CREATE"):
        return Fail(msg="无权限创建员工")
    current_emp = await employee_controller.get_or_none(user_id=CTX_USER_ID.get())
    return await create_employee(emp_in, current_emp, request.app.state.redis)


@router.patch("/employees/{emp_id}", summary="更新员工")
async def update_emp(emp_id: int, emp_in: EmployeeUpdate):
    return await update_employee(emp_id, emp_in)
