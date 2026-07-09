import pytest
from httpx import AsyncClient

from app.core.code import Code
from app.core.sqids import encode_id
from app.system.models import Api, Button, Menu, MenuType, StatusType

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.fixture
async def home_menu_id(seed_data) -> str:
    menu = await Menu.filter(route_name="home").first()
    assert menu is not None
    return encode_id(menu.id)


class TestRoleList:
    async def test_get_role_list(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/api/v1/system-manage/roles/search",
            json={
                "current": 1,
                "size": 10,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"
        assert "records" in data["data"]
        assert len(data["data"]["records"]) >= 3  # R_SUPER, R_ADMIN, R_USER

    async def test_get_role_list_filter_by_name(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/api/v1/system-manage/roles/search",
            json={
                "current": 1,
                "size": 10,
                "roleName": "超级",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"
        records = data["data"]["records"]
        assert len(records) >= 1


class TestRoleCRUD:
    async def test_create_role(self, auth_client: AsyncClient, home_menu_id: str):
        resp = await auth_client.post(
            "/api/v1/system-manage/roles",
            json={
                "roleName": "测试角色",
                "roleCode": "R_TEST",
                "roleDesc": "测试角色描述",
                "byRoleHomeId": home_menu_id,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"
        assert "createdId" in data["data"]

    async def test_create_role_duplicate_code(self, auth_client: AsyncClient, home_menu_id: str):
        # R_SUPER already exists
        resp = await auth_client.post(
            "/api/v1/system-manage/roles",
            json={
                "roleName": "重复角色",
                "roleCode": "R_SUPER",
                "roleDesc": "重复",
                "byRoleHomeId": home_menu_id,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == Code.DUPLICATE_ROLE_CODE

    async def test_create_role_requires_home_menu(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/api/v1/system-manage/roles",
            json={
                "roleName": "无首页角色",
                "roleCode": "R_NO_HOME_TEST",
                "roleDesc": "无首页角色",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == Code.REQUEST_VALIDATION

    async def test_update_role(self, auth_client: AsyncClient, home_menu_id: str):
        # Create a role first
        create_resp = await auth_client.post(
            "/api/v1/system-manage/roles",
            json={
                "roleName": "待更新角色",
                "roleCode": "R_UPDATE_TEST",
                "roleDesc": "待更新",
                "byRoleHomeId": home_menu_id,
            },
        )
        role_id = create_resp.json()["data"]["createdId"]

        resp = await auth_client.patch(
            f"/api/v1/system-manage/roles/{role_id}",
            json={
                "roleDesc": "已更新描述",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"

    async def test_delete_role(self, auth_client: AsyncClient, home_menu_id: str):
        # Create a role first
        create_resp = await auth_client.post(
            "/api/v1/system-manage/roles",
            json={
                "roleName": "待删除角色",
                "roleCode": "R_DELETE_TEST",
                "roleDesc": "待删除",
                "byRoleHomeId": home_menu_id,
            },
        )
        role_id = create_resp.json()["data"]["createdId"]

        resp = await auth_client.delete(f"/api/v1/system-manage/roles/{role_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"

    async def test_get_role_list_no_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/system-manage/roles/search", json={"current": 1, "size": 10})
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == Code.INVALID_TOKEN


class TestRoleButtonAuth:
    async def test_role_button_ids_use_sqid(self, auth_client: AsyncClient, home_menu_id: str):
        create_resp = await auth_client.post(
            "/api/v1/system-manage/roles",
            json={
                "roleName": "按钮权限角色",
                "roleCode": "R_BUTTON_AUTH_TEST",
                "roleDesc": "按钮权限角色",
                "byRoleHomeId": home_menu_id,
            },
        )
        role_id = create_resp.json()["data"]["createdId"]
        button = await Button.create(button_code="B_ROLE_BUTTON_AUTH", button_desc="角色按钮权限")
        button_id = encode_id(button.id)

        update_resp = await auth_client.patch(
            f"/api/v1/system-manage/roles/{role_id}/buttons",
            json={"byRoleButtonIds": [button_id]},
        )
        assert update_resp.status_code == 200
        update_data = update_resp.json()
        assert update_data["code"] == "0000"
        assert update_data["data"]["byRoleButtonIds"] == [button_id]

        get_resp = await auth_client.get(f"/api/v1/system-manage/roles/{role_id}/buttons")
        assert get_resp.status_code == 200
        get_data = get_resp.json()
        assert get_data["code"] == "0000"
        assert get_data["data"]["byRoleButtonIds"] == [button_id]


class TestRoleMenuAuth:
    async def test_role_menu_home_id_uses_sqid(self, auth_client: AsyncClient, home_menu_id: str):
        create_resp = await auth_client.post(
            "/api/v1/system-manage/roles",
            json={
                "roleName": "菜单首页权限角色",
                "roleCode": "R_MENU_AUTH_TEST",
                "roleDesc": "菜单首页权限角色",
                "byRoleHomeId": home_menu_id,
            },
        )
        role_id = create_resp.json()["data"]["createdId"]

        get_resp = await auth_client.get(f"/api/v1/system-manage/roles/{role_id}/menus")
        assert get_resp.status_code == 200
        get_data = get_resp.json()
        assert get_data["code"] == "0000"
        assert get_data["data"]["byRoleHomeId"] == home_menu_id

    async def test_role_menu_ids_use_sqid(self, auth_client: AsyncClient, home_menu_id: str):
        create_resp = await auth_client.post(
            "/api/v1/system-manage/roles",
            json={
                "roleName": "菜单权限角色",
                "roleCode": "R_MENU_IDS_TEST",
                "roleDesc": "菜单权限角色",
                "byRoleHomeId": home_menu_id,
            },
        )
        role_id = create_resp.json()["data"]["createdId"]
        menu = await Menu.create(
            menu_name="菜单权限测试",
            menu_type="2",
            route_name="role_menu_ids_test",
            route_path="/role-menu-ids-test",
            status_type="1",
            constant=False,
        )
        menu_id = encode_id(menu.id)

        tree_resp = await auth_client.get("/api/v1/system-manage/menus/tree")
        assert tree_resp.status_code == 200
        tree_data = tree_resp.json()
        assert tree_data["code"] == "0000"
        assert any(item["resourceId"] == menu_id for item in tree_data["data"])

        update_resp = await auth_client.patch(
            f"/api/v1/system-manage/roles/{role_id}/menus",
            json={"byRoleHomeId": home_menu_id, "byRoleMenuIds": [menu_id]},
        )
        assert update_resp.status_code == 200
        update_data = update_resp.json()
        assert update_data["code"] == "0000"
        assert set(update_data["data"]["byRoleMenuIds"]) == {menu_id, home_menu_id}

        get_resp = await auth_client.get(f"/api/v1/system-manage/roles/{role_id}/menus")
        assert get_resp.status_code == 200
        get_data = get_resp.json()
        assert get_data["code"] == "0000"
        assert set(get_data["data"]["byRoleMenuIds"]) == {menu_id, home_menu_id}

    async def test_role_menu_ids_return_leaf_sqids(self, auth_client: AsyncClient, home_menu_id: str):
        create_resp = await auth_client.post(
            "/api/v1/system-manage/roles",
            json={
                "roleName": "叶子菜单权限角色",
                "roleCode": "R_MENU_LEAF_IDS_TEST",
                "roleDesc": "叶子菜单权限角色",
                "byRoleHomeId": home_menu_id,
            },
        )
        role_id = create_resp.json()["data"]["createdId"]
        parent = await Menu.create(
            menu_name="叶子权限父菜单",
            menu_type=MenuType.catalog,
            route_name="role_menu_leaf_parent",
            route_path="/role-menu-leaf-parent",
            component="layout.base",
            status_type=StatusType.enable,
            constant=False,
        )
        child = await Menu.create(
            menu_name="叶子权限子菜单",
            menu_type=MenuType.menu,
            route_name="role_menu_leaf_child",
            route_path="/role-menu-leaf-parent/child",
            component="view.home",
            parent_id=parent.id,
            status_type=StatusType.enable,
            constant=False,
        )
        child_id = encode_id(child.id)

        update_resp = await auth_client.patch(
            f"/api/v1/system-manage/roles/{role_id}/menus",
            json={"byRoleHomeId": home_menu_id, "byRoleMenuIds": [child_id]},
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["code"] == "0000"

        get_resp = await auth_client.get(f"/api/v1/system-manage/roles/{role_id}/menus")
        assert get_resp.status_code == 200
        get_data = get_resp.json()
        assert get_data["code"] == "0000"
        assert set(get_data["data"]["byRoleMenuIds"]) == {child_id, home_menu_id}

    async def test_role_menu_update_includes_home_menu(self, auth_client: AsyncClient, home_menu_id: str):
        create_resp = await auth_client.post(
            "/api/v1/system-manage/roles",
            json={
                "roleName": "首页菜单权限角色",
                "roleCode": "R_MENU_HOME_TEST",
                "roleDesc": "首页菜单权限角色",
                "byRoleHomeId": home_menu_id,
            },
        )
        role_id = create_resp.json()["data"]["createdId"]

        update_resp = await auth_client.patch(
            f"/api/v1/system-manage/roles/{role_id}/menus",
            json={"byRoleHomeId": home_menu_id, "byRoleMenuIds": []},
        )
        assert update_resp.status_code == 200
        update_data = update_resp.json()
        assert update_data["code"] == "0000"
        assert update_data["data"]["byRoleMenuIds"] == [home_menu_id]

        get_resp = await auth_client.get(f"/api/v1/system-manage/roles/{role_id}/menus")
        assert get_resp.status_code == 200
        get_data = get_resp.json()
        assert get_data["code"] == "0000"
        assert get_data["data"]["byRoleMenuIds"] == [home_menu_id]


class TestRoleApiAuth:
    async def test_role_api_ids_use_sqid(self, auth_client: AsyncClient, home_menu_id: str):
        create_resp = await auth_client.post(
            "/api/v1/system-manage/roles",
            json={
                "roleName": "API权限角色",
                "roleCode": "R_API_IDS_TEST",
                "roleDesc": "API权限角色",
                "byRoleHomeId": home_menu_id,
            },
        )
        role_id = create_resp.json()["data"]["createdId"]
        api = await Api.create(
            api_path="/api/v1/test/role-api-ids",
            api_method="get",
            summary="角色API权限测试",
            tags=["角色API权限"],
            status_type="1",
        )
        api_id = encode_id(api.id)

        tree_resp = await auth_client.get("/api/v1/system-manage/apis/tree")
        assert tree_resp.status_code == 200
        tree_data = tree_resp.json()
        assert tree_data["code"] == "0000"
        parent_node = next(node for node in tree_data["data"] if node["label"] == "角色API权限")
        assert parent_node["isParent"] is True
        assert parent_node["resourceId"] is None
        assert not {"id", "summary"} & parent_node.keys()
        assert any(child["resourceId"] == api_id and child["isParent"] is False for child in parent_node.get("children", []))

        update_resp = await auth_client.patch(
            f"/api/v1/system-manage/roles/{role_id}/apis",
            json={"byRoleApiIds": [api_id]},
        )
        assert update_resp.status_code == 200
        update_data = update_resp.json()
        assert update_data["code"] == "0000"
        assert update_data["data"]["byRoleApiIds"] == [api_id]

        get_resp = await auth_client.get(f"/api/v1/system-manage/roles/{role_id}/apis")
        assert get_resp.status_code == 200
        get_data = get_resp.json()
        assert get_data["code"] == "0000"
        assert get_data["data"]["byRoleApiIds"] == [api_id]
