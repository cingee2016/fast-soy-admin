import pytest
from httpx import AsyncClient

from app.core.cache import get_role_apis, load_role_permissions
from app.core.sqids import encode_id
from app.system.models import Api, Role, StatusType

pytestmark = pytest.mark.asyncio(loop_scope="session")


class TestApiManagement:
    async def test_update_api_status_refreshes_role_permission_cache(self, auth_client: AsyncClient, app):
        role = await Role.get(role_code="R_USER")
        api = await Api.create(
            api_path="/api/v1/test/api-status-toggle",
            api_method="get",
            summary="API状态切换测试",
            tags=["API管理"],
            status_type=StatusType.enable,
        )
        await role.by_role_apis.add(api)
        await load_role_permissions(app.state.redis, role_code=role.role_code)

        before = await get_role_apis(app.state.redis, role.role_code)
        assert any(item["path"] == api.api_path and item["status"] == StatusType.enable.value for item in before)

        resp = await auth_client.patch(
            f"/api/v1/system-manage/apis/{encode_id(api.id)}/status",
            json={"statusType": StatusType.disable.value},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"
        assert data["data"]["updatedId"] == encode_id(api.id)

        await api.refresh_from_db()
        assert api.status_type == StatusType.disable

        after = await get_role_apis(app.state.redis, role.role_code)
        assert any(item["path"] == api.api_path and item["status"] == StatusType.disable.value for item in after)
