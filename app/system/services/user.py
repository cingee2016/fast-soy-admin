"""
系统用户服务。

这里放置 system 领域自己的用户编排逻辑；
业务模块如需复用，统一通过 ``app.utils`` 暴露的公共 API 访问。
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass

from redis.asyncio import Redis

from app.core.cache import refresh_user_roles
from app.system.controllers import role_controller
from app.system.controllers.user import UserCreate, user_controller
from app.system.models import User


@dataclass
class CreateUserResult:
    user: User
    raw_password: str


async def create_system_user(
    redis: Redis,
    *,
    user_name: str,
    nick_name: str,
    user_email: str,
    user_gender: str | None = None,
    user_phone: str | None = None,
    role_codes: list[str] | None = None,
) -> CreateUserResult:
    """
    创建系统用户。

    - 自动生成随机密码
    - 设置 must_change_password = True
    - 分配角色（默认 R_USER）
    - 刷新 Redis 缓存

    Returns:
        CreateUserResult(user, raw_password)

    Raises:
        ValueError: 用户名或邮箱已存在
    """
    if await user_controller.get_by_username(user_name):
        raise ValueError(f"用户名 {user_name} 已存在")
    if await user_controller.get_by_email(user_email):
        raise ValueError(f"邮箱 {user_email} 已被使用")

    raw_password = secrets.token_urlsafe(10)

    new_user = await user_controller.create(
        UserCreate(
            userName=user_name,  # type: ignore[call-arg]
            nickName=nick_name,  # type: ignore[call-arg]
            userEmail=user_email,  # type: ignore[call-arg]
            userGender=user_gender,  # type: ignore[call-arg]
            userPhone=user_phone,  # type: ignore[call-arg]
            password=raw_password,
        )
    )

    await User.filter(id=new_user.id).update(must_change_password=True)

    for code in role_codes or ["R_USER"]:
        role = await role_controller.get_by_code(code)
        if role:
            await new_user.by_user_roles.add(role)

    await refresh_user_roles(redis, new_user.id)

    return CreateUserResult(user=new_user, raw_password=raw_password)
