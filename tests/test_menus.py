import pytest
from httpx import AsyncClient

from app.core.code import Code
from app.core.sqids import encode_id
from app.system.models import Button, Menu, MenuType, StatusType

pytestmark = pytest.mark.asyncio(loop_scope="session")


class TestMenuList:
    async def test_get_menu_list(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/system-manage/menus/search", json={"current": 1, "size": 100})
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"
        assert "records" in data["data"]

    async def test_get_menu_tree(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/system-manage/menus/tree")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"

    async def test_get_menu_pages(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/system-manage/menus/pages")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"

    async def test_get_menu_buttons_tree(self, auth_client: AsyncClient):
        menu = await Menu.create(
            menu_name="ButtonTreeMenu",
            menu_type=MenuType.menu,
            route_name="button_tree_menu",
            route_path="/button-tree-menu",
            status_type=StatusType.enable,
            constant=False,
        )
        button = await Button.create(button_code="B_TEST_TREE_ACTION", button_desc="测试按钮名")
        await menu.by_menu_buttons.add(button)

        resp = await auth_client.get("/api/v1/system-manage/menus/buttons/tree")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"

        def collect_leaf_nodes(nodes: list[dict]) -> list[dict]:
            leaves: list[dict] = []
            for node in nodes:
                children = node.get("children") or []
                if children:
                    leaves.extend(collect_leaf_nodes(children))
                elif not str(node["id"]).startswith("parent$"):
                    leaves.append(node)
            return leaves

        leaf_nodes = collect_leaf_nodes(data["data"])

        def collect_leaf_labels(nodes: list[dict]) -> list[str]:
            labels: list[str] = []
            for node in nodes:
                children = node.get("children") or []
                if children:
                    labels.extend(collect_leaf_labels(children))
                elif not str(node["id"]).startswith("parent$"):
                    labels.append(node["label"])
            return labels

        assert "测试按钮名" in collect_leaf_labels(data["data"])
        assert "B_TEST_TREE_ACTION" not in collect_leaf_labels(data["data"])
        assert any(node["id"] == encode_id(button.id) for node in leaf_nodes)


class TestMenuCRUD:
    async def test_create_menu(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/api/v1/system-manage/menus",
            json={
                "menuName": "TestMenu",
                "menuType": "2",
                "routeName": "test_menu",
                "routePath": "/test-menu",
                "status": "1",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"
        assert "createdId" in data["data"]

    async def test_create_menu_duplicate_route_path(self, auth_client: AsyncClient):
        # First create
        await auth_client.post(
            "/api/v1/system-manage/menus",
            json={
                "menuName": "DupMenu",
                "menuType": "2",
                "routeName": "dup_menu",
                "routePath": "/dup-menu",
                "status": "1",
            },
        )
        # Duplicate
        resp = await auth_client.post(
            "/api/v1/system-manage/menus",
            json={
                "menuName": "DupMenu2",
                "menuType": "2",
                "routeName": "dup_menu2",
                "routePath": "/dup-menu",
                "status": "1",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == Code.DUPLICATE_MENU_ROUTE

    async def test_update_menu(self, auth_client: AsyncClient):
        # Create
        create_resp = await auth_client.post(
            "/api/v1/system-manage/menus",
            json={
                "menuName": "UpdateMe",
                "menuType": "2",
                "routeName": "update_me_menu",
                "routePath": "/update-me",
                "status": "1",
            },
        )
        menu_id = create_resp.json()["data"]["createdId"]

        resp = await auth_client.patch(
            f"/api/v1/system-manage/menus/{menu_id}",
            json={"menuName": "UpdatedMenu"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"

    async def test_delete_menu(self, auth_client: AsyncClient):
        # Create
        create_resp = await auth_client.post(
            "/api/v1/system-manage/menus",
            json={
                "menuName": "DeleteMe",
                "menuType": "2",
                "routeName": "delete_me_menu",
                "routePath": "/delete-me",
                "status": "1",
            },
        )
        menu_id = create_resp.json()["data"]["createdId"]

        resp = await auth_client.delete(f"/api/v1/system-manage/menus/{menu_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"

    async def test_menu_no_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/system-manage/menus/search", json={"current": 1, "size": 10})
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == Code.INVALID_TOKEN
