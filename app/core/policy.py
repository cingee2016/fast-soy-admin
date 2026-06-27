from __future__ import annotations

import inspect

from tortoise.expressions import Q

from app.core.business import DataPolicy, PolicyContext
from app.core.code import Code
from app.core.ctx import CTX_BUTTON_CODES, CTX_ROLE_CODES, CTX_USER_ID, is_super_admin
from app.core.exceptions import BizError

_data_policies: dict[str, DataPolicy] = {}


def register_data_policy(policy: DataPolicy) -> None:
    """Register one data policy by name."""

    existing = _data_policies.get(policy.name)
    if existing is not None and existing is not policy:
        raise RuntimeError(f"Duplicate data policy: {policy.name}")
    _data_policies[policy.name] = policy


def register_data_policies(policies: list[DataPolicy]) -> None:
    for policy in policies:
        register_data_policy(policy)


def get_data_policy(name: str) -> DataPolicy:
    try:
        return _data_policies[name]
    except KeyError as exc:
        raise RuntimeError(f"Data policy not registered: {name}") from exc


def build_policy_context(*, redis=None, module: str | None = None) -> PolicyContext:
    return PolicyContext(
        user_id=CTX_USER_ID.get(),
        role_codes=list(CTX_ROLE_CODES.get() or []),
        button_codes=list(CTX_BUTTON_CODES.get() or []),
        is_super=is_super_admin(),
        redis=redis,
        module=module,
    )


async def apply_data_policy(name: str, *, redis=None, module: str | None = None) -> Q:
    policy = get_data_policy(name)
    if policy.build_filter is None:
        raise RuntimeError(f"Data policy {name!r} does not provide a filter builder")
    ctx = build_policy_context(redis=redis, module=module)
    result = policy.build_filter(ctx)
    if inspect.isawaitable(result):
        result = await result
    if not isinstance(result, Q):
        raise RuntimeError(f"Data policy {name!r} must return tortoise.expressions.Q")
    return result


async def check_object_policy(name: str, obj, *, redis=None, module: str | None = None) -> bool:
    policy = get_data_policy(name)
    if policy.check_object is None:
        raise RuntimeError(f"Data policy {name!r} does not provide an object checker")
    ctx = build_policy_context(redis=redis, module=module)
    result = policy.check_object(ctx, obj)
    if inspect.isawaitable(result):
        result = await result
    return bool(result)


async def assert_object_policy(name: str, obj, *, redis=None, module: str | None = None) -> None:
    allowed = await check_object_policy(name, obj, redis=redis, module=module)
    if not allowed:
        raise BizError(code=Code.PERMISSION_DENIED, msg="数据权限不足")


def list_data_policy_names() -> list[str]:
    return sorted(_data_policies)
