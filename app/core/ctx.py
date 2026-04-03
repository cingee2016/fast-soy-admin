from __future__ import annotations

import contextvars
from typing import TYPE_CHECKING

from starlette.background import BackgroundTasks

if TYPE_CHECKING:
    from app.system.models import User

CTX_USER_ID: contextvars.ContextVar[int] = contextvars.ContextVar("user_id", default=0)
CTX_X_REQUEST_ID: contextvars.ContextVar[str] = contextvars.ContextVar("x_request_id", default="")
CTX_BG_TASKS: contextvars.ContextVar[BackgroundTasks | None] = contextvars.ContextVar("bg_task", default=None)

CTX_USER: contextvars.ContextVar[User | None] = contextvars.ContextVar("user", default=None)
CTX_ROLE_CODES: contextvars.ContextVar[list[str]] = contextvars.ContextVar("role_codes", default=[])
CTX_BUTTON_CODES: contextvars.ContextVar[list[str]] = contextvars.ContextVar("button_codes", default=[])
CTX_IMPERSONATOR_ID: contextvars.ContextVar[int] = contextvars.ContextVar("impersonator_id", default=0)


def get_current_user() -> User | None:
    """获取当前请求的用户对象"""
    return CTX_USER.get()


def is_super_admin() -> bool:
    """判断当前用户是否是超级管理员"""
    return "R_SUPER" in CTX_ROLE_CODES.get()


def has_role_code(code: str) -> bool:
    """判断当前用户是否拥有指定角色，超级管理员直接返回 True"""
    role_codes = CTX_ROLE_CODES.get()
    return "R_SUPER" in role_codes or code in role_codes


def has_button_code(code: str) -> bool:
    """判断当前用户是否拥有指定按钮权限，超级管理员直接返回 True"""
    if "R_SUPER" in CTX_ROLE_CODES.get():
        return True
    return code in CTX_BUTTON_CODES.get()
