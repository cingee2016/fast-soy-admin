"""
HR 公开接口（常量路由数据展示页）— 无需登录即可访问，仅返回聚合统计。

⚠️ 这些接口不经过 DependAuth / DependPermission，**不要**在这里暴露任何敏感字段
（手机号、邮箱、工号、user_id 等）。
"""

from __future__ import annotations

from fastapi import APIRouter

from app.business.hr.services import get_public_showcase_overview
from app.utils import Success

router = APIRouter(prefix="/public", tags=["HR公开展示"])


@router.get("/showcase", summary="[公开] HR 数据展示总览", name="hr.public.showcase")
async def showcase_overview():
    """返回部门 / 员工 / 标签的公开聚合统计，用于常量路由展示页。"""
    return Success(data=await get_public_showcase_overview())
