"""
Business dependencies — 员工身份解析 & 主管权限。

Usage:
    @router.get("/my/profile", dependencies=[DependAuth])
    async def my_profile(emp: Employee = DependEmployee):
        ...

    @router.patch("/department/employees/{id}/tags")
    async def edit_tags(emp: Employee = DependManager):
        ...
"""

from __future__ import annotations

from typing import Any

from fastapi import Depends

from app.business.hr.ctx import set_current_department_id
from app.business.hr.models import Department, Employee
from app.utils import BizError, Code, DependAuth, get_current_user_id


async def _get_employee_for_user(user_id: int) -> Employee | None:
    return await Employee.filter(user_id=user_id).select_related("department").first()


async def bind_hr_scope_context(_: Any = DependAuth) -> None:
    """Bind current user's department as HR's request-local business scope."""
    user_id = get_current_user_id()
    emp = await _get_employee_for_user(user_id) if user_id is not None else None
    set_current_department_id(emp.department_id if emp else None)


async def get_current_employee(_: Any = DependAuth) -> Employee:
    """解析当前用户对应的员工，并将部门 ID 写入上下文"""
    user_id = get_current_user_id()
    emp = await _get_employee_for_user(user_id) if user_id is not None else None
    if not emp:
        set_current_department_id(None)
        raise BizError(code=Code.HR_USER_NOT_EMPLOYEE, msg="当前用户未关联员工信息")
    set_current_department_id(emp.department_id)
    return emp


async def get_department_manager(emp: Employee = Depends(get_current_employee)) -> Employee:
    """校验当前员工是否为部门主管"""
    is_mgr = await Department.filter(id=emp.department_id, manager_id=emp.id).exists()
    if not is_mgr:
        raise BizError(code=Code.HR_MANAGER_ONLY, msg="仅部门主管可执行此操作")
    return emp


DependHrScope = Depends(bind_hr_scope_context)
DependEmployee = Depends(get_current_employee)
DependManager = Depends(get_department_manager)
