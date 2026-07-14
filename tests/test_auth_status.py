from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.cache import clear_role_permissions, get_user_role_codes, refresh_user_roles
from app.core.code import Code
from app.core.config import APP_SETTINGS
from app.core.sqids import encode_id
from app.system.models import Menu, Role, StatusType, User
from app.system.schemas.login import JWTPayload
from app.system.schemas.users import UserUpdate
from app.system.security import create_access_token, get_password_hash
from app.system.services.user import update_managed_user

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _access_token(user: User, token_version: int = 0) -> str:
    now = datetime.now(UTC)
    payload = JWTPayload(
        data={
            "userId": user.id,
            "userName": user.user_name,
            "tokenType": "accessToken",
            "tokenVersion": token_version,
        },
        iat=now,
        exp=now + timedelta(minutes=APP_SETTINGS.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return create_access_token(data=payload)


async def _client_for(app, user: User) -> AsyncClient:
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers={"Authorization": f"Bearer {_access_token(user)}"},
    )


async def test_disabled_user_rejects_old_token_and_reenabled_user_cannot_reuse_it(app, seed_data):
    redis = app.state.redis
    role = await Role.get(role_code="R_USER")
    await Role.filter(id=role.id).update(status_type=StatusType.enable)
    user = await User.create(
        user_name="auth_status_user",
        password=get_password_hash("123456"),
        nick_name="认证状态测试",
    )
    await user.by_user_roles.add(role)
    await refresh_user_roles(redis, user.id)

    try:
        async with await _client_for(app, user) as client:
            before = await client.get("/api/v1/auth/user-info")
            assert before.json()["code"] == Code.SUCCESS

            await update_managed_user(
                redis,
                user.id,
                UserUpdate(statusType=StatusType.disable, byUserRoleCodeList=["R_USER"]),  # type: ignore[call-arg]
            )

            disabled = await client.get("/api/v1/auth/user-info")
            assert disabled.json()["code"] == Code.ACCOUNT_DISABLED

            disabled_login = await client.post(
                "/api/v1/auth/login",
                json={"userName": user.user_name, "password": "123456"},
            )
            assert disabled_login.json()["code"] == Code.ACCOUNT_DISABLED

            await update_managed_user(
                redis,
                user.id,
                UserUpdate(statusType=StatusType.enable, byUserRoleCodeList=["R_USER"]),  # type: ignore[call-arg]
            )

            stale = await client.get("/api/v1/auth/user-info")
            assert stale.json()["code"] == Code.SESSION_INVALIDATED

            fresh_login = await client.post(
                "/api/v1/auth/login",
                json={"userName": user.user_name, "password": "123456"},
            )
            assert fresh_login.json()["code"] == Code.SUCCESS

            await update_managed_user(
                redis,
                user.id,
                UserUpdate(statusType=StatusType.invalid, byUserRoleCodeList=["R_USER"]),  # type: ignore[call-arg]
            )
            invalid_login = await client.post(
                "/api/v1/auth/login",
                json={"userName": user.user_name, "password": "123456"},
            )
            assert invalid_login.json()["code"] == Code.ACCOUNT_DISABLED
    finally:
        await redis.delete(f"user:{user.id}:roles", f"user:{user.id}:role_home", f"token_version:{user.id}")
        await user.delete()


async def test_user_role_update_refreshes_role_cache(app, seed_data):
    redis = app.state.redis
    home = await Menu.get(route_name="home")
    role_a = await Role.create(role_name="缓存角色A", role_code="R_CACHE_A", by_role_home=home)
    role_b = await Role.create(role_name="缓存角色B", role_code="R_CACHE_B", by_role_home=home)
    user = await User.create(user_name="role_cache_user", password=get_password_hash("123456"))
    await user.by_user_roles.add(role_a)
    await refresh_user_roles(redis, user.id)

    try:
        assert await get_user_role_codes(redis, user.id) == [role_a.role_code]

        await update_managed_user(
            redis,
            user.id,
            UserUpdate(byUserRoleCodeList=[role_b.role_code]),  # type: ignore[call-arg]
        )

        assert await get_user_role_codes(redis, user.id) == [role_b.role_code]
    finally:
        await redis.delete(f"user:{user.id}:roles", f"user:{user.id}:role_home")
        await user.delete()
        await role_a.delete()
        await role_b.delete()


async def test_role_status_and_code_update_refreshes_all_related_caches(app, auth_client, seed_data):
    redis = app.state.redis
    home = await Menu.get(route_name="home")
    old_code = "R_STATUS_CACHE_OLD"
    new_code = "R_STATUS_CACHE_NEW"
    role = await Role.create(role_name="状态缓存角色", role_code=old_code, by_role_home=home)
    role_id = encode_id(role.id)
    user = await User.create(user_name="role_status_user", password=get_password_hash("123456"))
    await user.by_user_roles.add(role)
    await refresh_user_roles(redis, user.id)

    try:
        disabled = await auth_client.patch(
            f"/api/v1/system-manage/roles/{role_id}",
            json={"statusType": StatusType.disable.value},
        )
        assert disabled.json()["code"] == Code.SUCCESS
        assert await get_user_role_codes(redis, user.id) == []
        for suffix in ("menus", "apis", "buttons", "data_scope"):
            assert await redis.get(f"role:{old_code}:{suffix}") is None

        enabled = await auth_client.patch(
            f"/api/v1/system-manage/roles/{role_id}",
            json={"statusType": StatusType.enable.value, "roleCode": new_code},
        )
        assert enabled.json()["code"] == Code.SUCCESS
        assert await get_user_role_codes(redis, user.id) == [new_code]
        for suffix in ("menus", "apis", "buttons", "data_scope"):
            assert await redis.get(f"role:{old_code}:{suffix}") is None
            assert await redis.get(f"role:{new_code}:{suffix}") is not None
    finally:
        await redis.delete(f"user:{user.id}:roles", f"user:{user.id}:role_home")
        await clear_role_permissions(redis, {old_code, new_code})
        await user.delete()
        await role.delete()


async def test_permission_database_fallback_excludes_disabled_roles(app, seed_data, monkeypatch):
    redis = app.state.redis
    home = await Menu.get(route_name="home")
    enabled_role = await Role.create(role_name="启用降级角色", role_code="R_FALLBACK_ON", by_role_home=home)
    disabled_role = await Role.create(
        role_name="关闭降级角色",
        role_code="R_FALLBACK_OFF",
        by_role_home=home,
        status_type=StatusType.disable,
    )
    user = await User.create(user_name="fallback_status_user", password=get_password_hash("123456"))
    await user.by_user_roles.add(enabled_role, disabled_role)

    async def _redis_failure(*args, **kwargs):
        raise ConnectionError("forced Redis permission lookup failure")

    monkeypatch.setattr("app.core.dependency.get_user_role_codes", _redis_failure)
    monkeypatch.setattr("app.core.dependency.get_user_button_codes", _redis_failure)

    try:
        async with await _client_for(app, user) as client:
            response = await client.get("/api/v1/auth/user-info")
        assert response.json()["code"] == Code.SUCCESS
        assert response.json()["data"]["roles"] == [enabled_role.role_code]
    finally:
        await user.delete()
        await enabled_role.delete()
        await disabled_role.delete()
