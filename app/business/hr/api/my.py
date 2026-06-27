"""
HR 个人接口 — 任何已绑定员工身份的登录用户都能访问的"我的工作台"接口。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, UploadFile

from app.business.hr.controllers import employee_controller
from app.business.hr.dependency import DependEmployee
from app.business.hr.files import save_avatar
from app.business.hr.schemas import MyProfileUpdate, TagIds
from app.business.hr.services import get_employee_profile, list_department_employees, update_employee_tags
from app.utils import Success, require_buttons

if TYPE_CHECKING:
    from app.business.hr.models import Employee

router = APIRouter(tags=["HR个人"])


@router.get("/my/profile", summary="我的信息", name="hr.my.profile")
async def my_profile(emp: Employee = DependEmployee):
    record = await get_employee_profile(emp)
    return Success(data=record)


@router.patch("/my/profile", summary="编辑我的资料", name="hr.my.update")
async def update_my_profile(body: MyProfileUpdate, emp: Employee = DependEmployee):
    """员工自助维护：仅允许电话、邮箱。部门 / 职位 / 状态需主管或 HR 操作。"""
    await employee_controller.update(id=emp.id, obj_in=body, exclude={"tag_ids"})
    return Success(msg="更新成功")


@router.patch(
    "/my/tags",
    summary="编辑我的标签",
    name="hr.my.tags",
    dependencies=[require_buttons("B_HR_MY_TAG_EDIT")],
)
async def my_tags(body: TagIds, emp: Employee = DependEmployee):
    return await update_employee_tags(emp, body.tag_ids, log_label="编辑个人标签")


@router.get("/my/department", summary="同部门同事", name="hr.my.department")
async def my_department(emp: Employee = DependEmployee):
    """查看同部门同事（脱敏：不返回手机/邮箱）"""
    records = await list_department_employees(emp.department_id, exclude_fields=["phone", "email"])  # type: ignore[attr-defined]
    return Success(data=records)


@router.post(
    "/my/avatar",
    summary="上传我的头像",
    name="hr.my.avatar",
    dependencies=[require_buttons("B_HR_MY_AVATAR_EDIT")],
)
async def upload_my_avatar(file: UploadFile, emp: Employee = DependEmployee):
    avatar_url = await save_avatar(file)
    await employee_controller.update(id=emp.id, obj_in={"avatar": avatar_url})
    return Success(msg="头像上传成功", data={"avatarUrl": avatar_url})
