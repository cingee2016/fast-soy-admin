from __future__ import annotations

from typing import Any

from app.business.hr.ctx import get_current_department_id
from app.utils import DataPolicy, PolicyContext, build_scope_filter, get_current_data_scope


async def build_employee_read_filter(ctx: PolicyContext):
    scope = await get_current_data_scope(ctx.redis)
    return build_scope_filter(
        scope=scope,
        user_id=ctx.user_id,
        scope_id=get_current_department_id(),
        user_id_field="user_id",
        scope_id_field="department_id",
    )


async def can_manage_employee(ctx: PolicyContext, obj: Any) -> bool:
    if ctx.is_super or "R_HR_ADMIN" in ctx.role_codes:
        return True
    department_id = getattr(obj, "department_id", None)
    if department_id is None and isinstance(obj, dict):
        department_id = obj.get("department_id") or obj.get("departmentId")
    return department_id is not None and department_id == get_current_department_id()


EMPLOYEE_READ_POLICY = DataPolicy(name="hr.employees.read", action="read", build_filter=build_employee_read_filter)
EMPLOYEE_UPDATE_POLICY = DataPolicy(name="hr.employees.update", action="update", check_object=can_manage_employee)

HR_DATA_POLICIES = [EMPLOYEE_READ_POLICY, EMPLOYEE_UPDATE_POLICY]
