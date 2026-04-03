import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio(loop_scope="session")


class TestMenuList:
    async def test_get_menu_list(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/menus", params={"current": 1, "size": 100})
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"
        assert "records" in data["data"]

    async def test_get_menu_tree(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/menus/tree/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"

    async def test_get_menu_pages(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/menus/pages/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"

    async def test_get_menu_buttons_tree(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/menus/buttons/tree/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"


class TestMenuCRUD:
    async def test_create_menu(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/api/v1/menus",
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
        assert "created_id" in data["data"]

    async def test_create_menu_duplicate_route_path(self, auth_client: AsyncClient):
        # First create
        await auth_client.post(
            "/api/v1/menus",
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
            "/api/v1/menus",
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
        assert data["code"] != "0000"

    async def test_get_menu(self, auth_client: AsyncClient):
        # Create a menu to fetch
        create_resp = await auth_client.post(
            "/api/v1/menus",
            json={
                "menuName": "GetMe",
                "menuType": "2",
                "routeName": "get_me_menu",
                "routePath": "/get-me",
                "status": "1",
            },
        )
        menu_id = create_resp.json()["data"]["created_id"]

        resp = await auth_client.get(f"/api/v1/menus/{menu_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"
        assert data["data"]["menuName"] == "GetMe"

    async def test_update_menu(self, auth_client: AsyncClient):
        # Create
        create_resp = await auth_client.post(
            "/api/v1/menus",
            json={
                "menuName": "UpdateMe",
                "menuType": "2",
                "routeName": "update_me_menu",
                "routePath": "/update-me",
                "status": "1",
            },
        )
        menu_id = create_resp.json()["data"]["created_id"]

        resp = await auth_client.patch(
            f"/api/v1/menus/{menu_id}",
            json={"menuName": "UpdatedMenu"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"

    async def test_delete_menu(self, auth_client: AsyncClient):
        # Create
        create_resp = await auth_client.post(
            "/api/v1/menus",
            json={
                "menuName": "DeleteMe",
                "menuType": "2",
                "routeName": "delete_me_menu",
                "routePath": "/delete-me",
                "status": "1",
            },
        )
        menu_id = create_resp.json()["data"]["created_id"]

        resp = await auth_client.delete(f"/api/v1/menus/{menu_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"

    async def test_menu_no_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/menus")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] != "0000"
