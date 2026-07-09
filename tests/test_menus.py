import pytest
from httpx import AsyncClient

from app.core.code import Code
from app.core.sqids import decode_id, encode_id
from app.system.models import Button, Menu, MenuType, StatusType

pytestmark = pytest.mark.asyncio(loop_scope="session")


class TestMenuList:
    async def test_get_menu_list(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/system-manage/menus/search", json={"current": 1, "size": 100})
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"
        assert "records" in data["data"]
        assert any(record.get("parentId") is None for record in data["data"]["records"])

    async def test_get_menu_tree(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/system-manage/menus/tree")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"

        parent = await Menu.create(
            menu_name="MenuTreeParent",
            menu_type=MenuType.catalog,
            route_name="menu_tree_parent",
            route_path="/menu-tree-parent",
            status_type=StatusType.enable,
            constant=False,
        )
        child = await Menu.create(
            menu_name="MenuTreeChild",
            menu_type=MenuType.menu,
            route_name="menu_tree_parent_child",
            route_path="/menu-tree-parent/child",
            parent_id=parent.id,
            status_type=StatusType.enable,
            constant=False,
        )

        resp = await auth_client.get("/api/v1/system-manage/menus/tree")
        assert resp.status_code == 200
        data = resp.json()
        parent_node = next(item for item in data["data"] if item["label"] == "MenuTreeParent")
        child_node = next(item for item in parent_node["children"] if item["label"] == "MenuTreeChild")
        assert parent_node["key"] == f"menu:{encode_id(parent.id)}"
        assert parent_node["isParent"] is True
        assert parent_node["resourceId"] is None
        assert parent_node["routeName"] == "menu_tree_parent"
        assert parent_node["meta"] == {"hidden": False}
        assert not {"id", "pId", "component", "routePath", "href", "hideInMenu"} & parent_node.keys()
        assert child_node["key"] == f"menu:{encode_id(child.id)}"
        assert child_node["isParent"] is False
        assert child_node["resourceId"] == encode_id(child.id)
        assert not {"id", "pId", "component", "routePath", "href", "hideInMenu"} & child_node.keys()

        root_menu = await Menu.create(
            menu_name="MenuTreeRootMenu",
            menu_type=MenuType.menu,
            route_name="menu_tree_root_menu",
            route_path="/menu-tree-root-menu",
            status_type=StatusType.enable,
            constant=False,
        )
        empty_catalog = await Menu.create(
            menu_name="MenuTreeEmptyCatalog",
            menu_type=MenuType.catalog,
            route_name="menu_tree_empty_catalog",
            route_path="/menu-tree-empty-catalog",
            status_type=StatusType.enable,
            constant=False,
        )

        resp = await auth_client.get("/api/v1/system-manage/menus/tree")
        assert resp.status_code == 200
        data = resp.json()
        root_menu_node = next(item for item in data["data"] if item["label"] == "MenuTreeRootMenu")
        assert root_menu_node["key"] == f"menu:{encode_id(root_menu.id)}"
        assert root_menu_node["isParent"] is False
        assert root_menu_node["resourceId"] == encode_id(root_menu.id)
        assert "children" not in root_menu_node
        assert not any(item["key"] == f"menu:{encode_id(empty_catalog.id)}" for item in data["data"])

        hidden = await Menu.create(
            menu_name="MenuTreeHidden",
            menu_type=MenuType.menu,
            route_name="menu_tree_hidden",
            route_path="/menu-tree-hidden",
            hide_in_menu=True,
            status_type=StatusType.enable,
            constant=False,
        )
        hidden_id = encode_id(hidden.id)

        default_resp = await auth_client.get("/api/v1/system-manage/menus/tree")
        assert default_resp.status_code == 200
        assert not any(item["resourceId"] == hidden_id for item in default_resp.json()["data"])

        hidden_resp = await auth_client.get("/api/v1/system-manage/menus/tree?includeHidden=true")
        assert hidden_resp.status_code == 200
        hidden_node = next(item for item in hidden_resp.json()["data"] if item["resourceId"] == hidden_id)
        assert hidden_node["key"] == f"menu:{hidden_id}"
        assert hidden_node["isParent"] is False
        assert hidden_node["meta"] == {"hidden": True}

        active_child = await Menu.create(
            menu_name="MenuTreeActiveHiddenChild",
            menu_type=MenuType.menu,
            route_name="menu_tree_active_hidden_child",
            route_path="/menu-tree-parent/active-hidden-child",
            parent_id=0,
            active_menu_id=parent.id,
            hide_in_menu=True,
            status_type=StatusType.enable,
            constant=False,
        )

        default_resp = await auth_client.get("/api/v1/system-manage/menus/tree")
        assert default_resp.status_code == 200
        parent_node = next(item for item in default_resp.json()["data"] if item["label"] == "MenuTreeParent")
        assert "MenuTreeActiveHiddenChild" not in [item["label"] for item in parent_node["children"]]

        hidden_resp = await auth_client.get("/api/v1/system-manage/menus/tree?includeHidden=true")
        assert hidden_resp.status_code == 200
        parent_node = next(item for item in hidden_resp.json()["data"] if item["label"] == "MenuTreeParent")
        active_child_node = next(item for item in parent_node["children"] if item["label"] == "MenuTreeActiveHiddenChild")
        assert parent_node["key"] == f"menu:{encode_id(parent.id)}"
        assert parent_node["isParent"] is True
        assert parent_node["resourceId"] is None
        assert active_child_node["resourceId"] == encode_id(active_child.id)
        assert active_child_node["isParent"] is False
        assert active_child_node["meta"] == {"hidden": True}

        path_child = await Menu.create(
            menu_name="MenuTreePathHiddenChild",
            menu_type=MenuType.menu,
            route_name="menu_tree_path_hidden_child",
            route_path="/menu-tree-parent/path-hidden-child",
            parent_id=0,
            hide_in_menu=True,
            status_type=StatusType.enable,
            constant=False,
        )

        hidden_resp = await auth_client.get("/api/v1/system-manage/menus/tree?includeHidden=true")
        assert hidden_resp.status_code == 200
        parent_node = next(item for item in hidden_resp.json()["data"] if item["label"] == "MenuTreeParent")
        path_child_node = next(item for item in parent_node["children"] if item["label"] == "MenuTreePathHiddenChild")
        assert path_child_node["resourceId"] == encode_id(path_child.id)
        assert path_child_node["isParent"] is False
        assert path_child_node["meta"] == {"hidden": True}

        route_name_child = await Menu.create(
            menu_name="MenuTreeRouteNameHiddenChild",
            menu_type=MenuType.menu,
            route_name="menu_tree_root_menu-detail",
            route_path="/menu-tree-root-menu-detail/:id",
            parent_id=0,
            hide_in_menu=True,
            status_type=StatusType.enable,
            constant=False,
        )

        hidden_resp = await auth_client.get("/api/v1/system-manage/menus/tree?includeHidden=true")
        assert hidden_resp.status_code == 200
        root_menu_node = next(item for item in hidden_resp.json()["data"] if item["label"] == "MenuTreeRootMenu")
        route_name_child_node = next(
            item for item in root_menu_node["children"] if item["label"] == "MenuTreeRouteNameHiddenChild"
        )
        assert root_menu_node["key"] == f"menu:{encode_id(root_menu.id)}"
        assert root_menu_node["isParent"] is True
        assert root_menu_node["resourceId"] is None
        assert route_name_child_node["resourceId"] == encode_id(route_name_child.id)
        assert route_name_child_node["isParent"] is False
        assert route_name_child_node["meta"] == {"hidden": True}

    async def test_get_menu_pages(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/system-manage/menus/pages")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"
        menu = await Menu.filter(parent_id=0, constant=False).first()
        assert menu is not None
        page = next(item for item in data["data"] if item["key"] == menu.menu_name)
        assert page["value"] == encode_id(menu.id)

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
                elif not node["isParent"]:
                    leaves.append(node)
            return leaves

        leaf_nodes = collect_leaf_nodes(data["data"])

        def collect_leaf_labels(nodes: list[dict]) -> list[str]:
            labels: list[str] = []
            for node in nodes:
                children = node.get("children") or []
                if children:
                    labels.extend(collect_leaf_labels(children))
                elif not node["isParent"]:
                    labels.append(node["label"])
            return labels

        assert "测试按钮名" in collect_leaf_labels(data["data"])
        assert "B_TEST_TREE_ACTION" not in collect_leaf_labels(data["data"])
        assert any(node["resourceId"] == encode_id(button.id) for node in leaf_nodes)

        def find_menu_parent(nodes: list[dict]) -> dict | None:
            for node in nodes:
                if node["label"] == "ButtonTreeMenu":
                    return node
                found = find_menu_parent(node.get("children") or [])
                if found:
                    return found
            return None

        parent = find_menu_parent(data["data"])
        assert parent is not None
        assert parent["key"] == f"menu:{encode_id(menu.id)}"
        assert parent["isParent"] is True
        assert parent["resourceId"] is None
        assert not {"id", "pId"} & parent.keys()


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

    async def test_create_root_menu_accepts_parent_id_null(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/api/v1/system-manage/menus",
            json={
                "menuName": "RootMenuWithParentNull",
                "menuType": "1",
                "routeName": "root_menu_parent_null",
                "routePath": "/root-menu-parent-null",
                "parentId": None,
                "component": "layout.base",
                "statusType": "1",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0000"
        menu = await Menu.get(route_name="root_menu_parent_null")
        assert menu.parent_id == 0

    async def test_create_root_menu_rejects_parent_id_zero(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/api/v1/system-manage/menus",
            json={
                "menuName": "RootMenuWithParentZero",
                "menuType": "1",
                "routeName": "root_menu_parent_zero",
                "routePath": "/root-menu-parent-zero",
                "parentId": 0,
                "component": "layout.base",
                "statusType": "1",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == Code.REQUEST_VALIDATION

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

    async def test_update_menu(self, auth_client: AsyncClient, seed_data):
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
        menu = await Menu.get(id=decode_id(menu_id))
        assert menu.updated_by == seed_data.user_name

    async def test_menu_submit_fields_align_with_backend(self, auth_client: AsyncClient):
        create_resp = await auth_client.post(
            "/api/v1/system-manage/menus",
            json={
                "menuName": "ContractMenu",
                "menuType": "2",
                "routeName": "contract_menu",
                "routePath": "/contract-menu",
                "component": "view.home",
                "statusType": "1",
                "activeMenu": "首页",
                "hideInMenu": True,
                "routeParam": [{"key": "source", "value": "contract"}],
                "byMenuButtons": [{"buttonCode": "B_CONTRACT_MENU_TEST", "buttonDesc": "契约测试"}],
            },
        )
        assert create_resp.status_code == 200
        create_data = create_resp.json()
        assert create_data["code"] == "0000"

        menu_id = create_data["data"]["createdId"]
        menu = await Menu.get(id=decode_id(menu_id)).prefetch_related("active_menu", "by_menu_buttons")
        assert menu.route_param == [{"key": "source", "value": "contract"}]
        assert menu.active_menu is not None
        assert menu.active_menu.menu_name == "首页"
        buttons = await menu.by_menu_buttons.all()
        assert [button.button_code for button in buttons] == ["B_CONTRACT_MENU_TEST"]

        routes_resp = await auth_client.get("/api/v1/route/user-routes")
        assert routes_resp.status_code == 200
        routes_data = routes_resp.json()
        assert routes_data["code"] == "0000"

        def find_route(nodes: list[dict], name: str) -> dict | None:
            for node in nodes:
                if node["name"] == name:
                    return node
                found = find_route(node.get("children") or [], name)
                if found:
                    return found
            return None

        route = find_route(routes_data["data"]["routes"], "contract_menu")
        assert route is not None
        assert route["meta"]["query"] == [{"key": "source", "value": "contract"}]

        update_resp = await auth_client.patch(
            f"/api/v1/system-manage/menus/{menu_id}",
            json={"routeParam": None, "activeMenu": None, "byMenuButtons": []},
        )
        assert update_resp.status_code == 200
        update_data = update_resp.json()
        assert update_data["code"] == "0000"

        menu = await Menu.get(id=decode_id(menu_id)).prefetch_related("by_menu_buttons")
        assert menu.route_param is None
        assert menu.active_menu_id is None
        assert await menu.by_menu_buttons.all().count() == 0

    async def test_update_menu_accepts_null_route_param(self, auth_client: AsyncClient):
        create_resp = await auth_client.post(
            "/api/v1/system-manage/menus",
            json={
                "menuName": "UpdateRouteParamNull",
                "menuType": "1",
                "routeName": "update_route_param_null",
                "routePath": "/update-route-param-null",
                "parentId": None,
                "component": "layout.base",
                "statusType": "1",
            },
        )
        menu_id = create_resp.json()["data"]["createdId"]

        resp = await auth_client.patch(
            f"/api/v1/system-manage/menus/{menu_id}",
            json={
                "menuName": "UpdateRouteParamNull",
                "routeParam": None,
                "fmtCreatedAt": "2026-07-01 03:03:27",
                "createdAt": 1782846207458,
                "id": menu_id,
            },
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
