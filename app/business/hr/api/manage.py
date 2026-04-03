"""
HR 管理接口 — 部门/技能/员工的 CRUD (需要系统权限)。
"""

from fastapi import APIRouter, Request
from tortoise.expressions import Q
from tortoise.transactions import in_transaction

from app.business.hr.config import BIZ_SETTINGS
from app.business.hr.controllers import department_controller, employee_controller, skill_controller
from app.business.hr.models import Employee
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
from app.business.hr.services import create_employee, get_department_stats
from app.utils import CTX_USER_ID, CRUDRouter, DependPermission, Fail, SearchFieldConfig, Success, SuccessExtra, has_button_code, is_super_admin, radar_log

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
    summary_prefix="技能",
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
router.include_router(dept_crud.router)
router.include_router(skill_crud.router)
router.include_router(emp_crud.router)


@router.post("/employees/all/", summary="查看员工列表")
async def list_employees(obj_in: EmployeeSearch):
    q = employee_controller.build_search(obj_in, contains_fields=["name", "email"], exact_fields=["status"])
    if obj_in.department_id:
        q &= Q(department_id=obj_in.department_id)

    total, employees = await employee_controller.list(page=obj_in.current, page_size=obj_in.size, search=q, order=["id"])
    records = []
    for emp in employees:
        record = await emp.to_dict(exclude_fields=["phone"])
        await emp.fetch_related("department", "skills")
        record["departmentName"] = emp.department.name
        record["skillNames"] = [s.name for s in emp.skills]
        records.append(record)

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
    current_emp = await Employee.filter(user_id=CTX_USER_ID.get()).first()
    return await create_employee(emp_in, current_emp, request.app.state.redis)


@router.patch("/employees/{emp_id}", summary="更新员工")
async def update_emp(emp_id: int, emp_in: EmployeeUpdate):
    if emp_in.skill_ids and len(emp_in.skill_ids) > BIZ_SETTINGS.MAX_SKILLS_PER_EMPLOYEE:
        return Fail(msg=f"技能数量不能超过 {BIZ_SETTINGS.MAX_SKILLS_PER_EMPLOYEE}")

    async with in_transaction("conn_system"):
        emp = await employee_controller.update(id=emp_id, obj_in=emp_in, exclude={"skill_ids"})
        if emp_in.skill_ids is not None:
            await emp.skills.clear()
            for sid in emp_in.skill_ids:
                await emp.skills.add(await skill_controller.get(id=sid))

    radar_log("编辑员工", data={"employeeId": emp_id})
    return Success(msg="Updated Successfully", data={"updated_id": emp_id})


@router.get("/departments/stats", summary="部门统计")
async def dept_stats():
    stats = await get_department_stats()
    return Success(data=stats)
