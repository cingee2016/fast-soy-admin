"""
HR 团队接口 — 部门主管对本部门员工的管理（搜索/标签/转正/统计）。

所有路径均带 ``/hr/team`` 前缀；调用方必须为本部门主管（``DependManager``）。
具体写操作再叠加按钮码控制，便于前端按按钮显隐。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter

from app.business.hr.dependency import DependManager
from app.business.hr.schemas import (
    EmployeeRegularize,
    EmployeeSearch,
    TagIds,
)
from app.business.hr.services import (
    edit_subordinate_tags,
    get_team_overview,
    list_team_employees,
    regularize_subordinate,
)
from app.utils import SqidPath, Success, SuccessExtra, require_buttons

if TYPE_CHECKING:
    from app.business.hr.models import Employee

router = APIRouter(tags=["HR团队"])


@router.post("/team/employees/search", summary="[主管] 下属分页搜索", name="hr.team.list")
async def team_employees_search(obj_in: EmployeeSearch, mgr: Employee = DependManager):
    # 主管列表强制锁定本部门；默认隐藏离职员工，显式筛选 resigned 时才返回离职记录。
    total, records = await list_team_employees(mgr, obj_in)
    return SuccessExtra(data={"records": records}, total=total, current=obj_in.current, size=obj_in.size)


@router.get("/team/stats", summary="[主管] 部门概览", name="hr.team.stats")
async def team_stats(mgr: Employee = DependManager):
    data = await get_team_overview(mgr)
    return Success(data=data)


@router.patch(
    "/team/employees/{emp_id}/tags",
    summary="[主管] 编辑下属标签",
    name="hr.team.tags",
    dependencies=[require_buttons("B_HR_TEAM_TAG_EDIT")],
)
async def team_edit_subordinate_tags(emp_id: SqidPath, body: TagIds, mgr: Employee = DependManager):
    return await edit_subordinate_tags(mgr, emp_id, body.tag_ids)


@router.post(
    "/team/employees/{emp_id}/regularize",
    summary="[主管] 办理下属转正",
    name="hr.team.regularize",
    dependencies=[require_buttons("B_HR_TEAM_REGULARIZE")],
)
async def team_regularize_employee(emp_id: SqidPath, body: EmployeeRegularize, mgr: Employee = DependManager):
    return await regularize_subordinate(mgr, emp_id, remark=body.remark)
