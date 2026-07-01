from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.core.code import Code
from app.core.sqids import encode_id
from app.system.models import User

pytestmark = pytest.mark.asyncio(loop_scope="session")


class TestLogin:
    async def test_login_success(self, client: AsyncClient, seed_data):
        resp = await client.post(
            "/api/v1/auth/login",
            json={
                "userName": "Soybean",
                "password": "123456",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"
        assert "token" in data["data"]
        assert "refreshToken" in data["data"]

    async def test_login_wrong_password(self, client: AsyncClient, seed_data):
        resp = await client.post(
            "/api/v1/auth/login",
            json={
                "userName": "Soybean",
                "password": "wrong_password",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == Code.WRONG_CREDENTIALS

    async def test_login_nonexistent_user(self, client: AsyncClient, seed_data):
        resp = await client.post(
            "/api/v1/auth/login",
            json={
                "userName": "nonexistent_user_xyz",
                "password": "123456",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == Code.WRONG_CREDENTIALS


class TestRefreshToken:
    async def test_refresh_token_success(self, client: AsyncClient, seed_data):
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "userName": "Soybean",
                "password": "123456",
            },
        )
        tokens = login_resp.json()["data"]

        resp = await client.post(
            "/api/v1/auth/refresh-token",
            json={
                "token": tokens["token"],
                "refreshToken": tokens["refreshToken"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"
        assert "token" in data["data"]
        assert "refreshToken" in data["data"]

    async def test_refresh_token_invalid(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/refresh-token",
            json={
                "token": "invalid_token",
                "refreshToken": "invalid_token",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == Code.INVALID_TOKEN

    async def test_refresh_token_expired_requires_login(self, client: AsyncClient, seed_data):
        from app.system.schemas.login import JWTPayload
        from app.system.security import create_access_token

        now = datetime.now(UTC)
        payload = JWTPayload(
            data={
                "userId": seed_data.id,
                "userName": seed_data.user_name,
                "tokenType": "refreshToken",
                "tokenVersion": 0,
            },
            iat=now - timedelta(days=8),
            exp=now - timedelta(minutes=1),
        )

        resp = await client.post(
            "/api/v1/auth/refresh-token",
            json={
                "refreshToken": create_access_token(data=payload),
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == Code.REFRESH_TOKEN_EXPIRED
        assert data["msg"] == "登录已过期，请重新登录"


class TestResetPassword:
    async def _seed_phone_user(self, phone: str, user_name: str):
        """Create a user with the given phone, return the user."""
        from app.system.models import User
        from app.system.security import get_password_hash

        existing = await User.filter(user_phone=phone).first()
        if existing:
            return existing
        return await User.create(
            user_name=user_name,
            password=get_password_hash("old_password"),
            nick_name=user_name,
            user_phone=phone,
        )

    async def _set_captcha(self, app, phone: str, code: str = "123456"):
        await app.state.redis.set(f"captcha:{phone}", code, ex=300)

    async def test_reset_password_success(self, client: AsyncClient, app, seed_data):
        phone = "13800138001"
        user = await self._seed_phone_user(phone, f"reset_u_{phone[-4:]}")
        await self._set_captcha(app, phone, "123456")

        resp = await client.post(
            "/api/v1/auth/reset-password",
            json={"phone": phone, "code": "123456", "password": "new_password"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"

        # New password works for login
        login = await client.post(
            "/api/v1/auth/login",
            json={"userName": user.user_name, "password": "new_password"},
        )
        assert login.json()["code"] == "0000"

    async def test_reset_password_invalid_captcha(self, client: AsyncClient, app, seed_data):
        phone = "13800138002"
        await self._seed_phone_user(phone, f"reset_u_{phone[-4:]}")
        await self._set_captcha(app, phone, "999999")

        resp = await client.post(
            "/api/v1/auth/reset-password",
            json={"phone": phone, "code": "000000", "password": "new_password"},
        )
        assert resp.json()["code"] == Code.CAPTCHA_INVALID

    async def test_reset_password_phone_not_registered(self, client: AsyncClient, app, seed_data):
        phone = "13800138999"
        await self._set_captcha(app, phone, "123456")

        resp = await client.post(
            "/api/v1/auth/reset-password",
            json={"phone": phone, "code": "123456", "password": "new_password"},
        )
        assert resp.json()["code"] == Code.PHONE_NOT_REGISTERED

    async def test_reset_password_disabled_account(self, client: AsyncClient, app, seed_data):
        from app.system.models import StatusType, User

        phone = "13800138003"
        user = await self._seed_phone_user(phone, f"reset_u_{phone[-4:]}")
        await User.filter(id=user.id).update(status_type=StatusType.disable)
        await self._set_captcha(app, phone, "123456")

        resp = await client.post(
            "/api/v1/auth/reset-password",
            json={"phone": phone, "code": "123456", "password": "new_password"},
        )
        assert resp.json()["code"] == Code.ACCOUNT_DISABLED


class TestUserInfo:
    async def test_get_user_info(self, auth_client: AsyncClient, seed_data):
        resp = await auth_client.get("/api/v1/auth/user-info")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"
        assert data["data"]["userId"] == encode_id(seed_data.id)
        assert data["data"]["userName"] == "Soybean"
        assert "roles" in data["data"]

    async def test_get_user_info_no_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/user-info")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == Code.INVALID_TOKEN

    async def test_update_profile(self, auth_client: AsyncClient, seed_data):
        original = {
            "nick_name": seed_data.nick_name,
            "user_email": seed_data.user_email,
            "user_phone": seed_data.user_phone,
            "user_gender": seed_data.user_gender,
        }
        try:
            resp = await auth_client.patch(
                "/api/v1/auth/profile",
                json={
                    "nickName": "Soybean Profile",
                    "userEmail": "profile-update@test.com",
                    "userPhone": "18800009999",
                    "userGender": "2",
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["code"] == "0000"
            assert data["data"]["userId"] == encode_id(seed_data.id)
            assert data["data"]["nickName"] == "Soybean Profile"
            assert data["data"]["userEmail"] == "profile-update@test.com"
            assert data["data"]["userPhone"] == "18800009999"
            assert data["data"]["userGender"] == "2"

            user = await User.get(id=seed_data.id)
            assert user.nick_name == "Soybean Profile"
            assert user.user_email == "profile-update@test.com"
            assert user.user_phone == "18800009999"
            assert user.user_gender == "2"
        finally:
            await User.filter(id=seed_data.id).update(**original)

    async def test_update_profile_allows_empty_contacts(self, auth_client: AsyncClient, seed_data):
        original = {
            "user_email": seed_data.user_email,
            "user_phone": seed_data.user_phone,
        }
        try:
            resp = await auth_client.patch(
                "/api/v1/auth/profile",
                json={"userEmail": "", "userPhone": None},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["code"] == "0000"
            assert data["data"]["userEmail"] is None
            assert data["data"]["userPhone"] is None
        finally:
            await User.filter(id=seed_data.id).update(**original)

    async def test_update_profile_rejects_duplicate_email_and_phone(self, auth_client: AsyncClient):
        user_name = "profile_dup_user"
        await User.filter(user_name=user_name).delete()
        other = await User.create(
            user_name=user_name,
            password="x",
            user_email="profile-duplicate@test.com",
            user_phone="18800008888",
        )
        try:
            email_resp = await auth_client.patch(
                "/api/v1/auth/profile",
                json={"userEmail": other.user_email},
            )
            assert email_resp.json()["code"] == Code.DUPLICATE_USER_EMAIL

            phone_resp = await auth_client.patch(
                "/api/v1/auth/profile",
                json={"userPhone": other.user_phone},
            )
            assert phone_resp.json()["code"] == Code.DUPLICATE_USER_PHONE
        finally:
            await other.delete()
