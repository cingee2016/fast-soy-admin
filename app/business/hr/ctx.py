"""
Business module context variables.

Business-specific context that can be set by middleware or dependencies.
Usage:
    from app.business.hr.ctx import get_department_id, set_department_id

    # In a dependency or middleware
    set_department_id(dept_id)

    # In business logic
    dept_id = get_department_id()
"""

from __future__ import annotations

import contextvars

# 当前操作的部门 ID（可用于部门范围的数据隔离）
CTX_DEPARTMENT_ID: contextvars.ContextVar[int | None] = contextvars.ContextVar("biz_department_id", default=None)


def get_department_id() -> int | None:
    """获取当前上下文中的部门 ID"""
    return CTX_DEPARTMENT_ID.get()


def set_department_id(dept_id: int | None) -> None:
    """设置当前上下文中的部门 ID"""
    CTX_DEPARTMENT_ID.set(dept_id)
