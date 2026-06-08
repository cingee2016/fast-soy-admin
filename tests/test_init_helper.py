import pytest

from app.system.services import init_helper

pytestmark = pytest.mark.asyncio


async def test_apply_init_data_applies_menus_roles_users_and_dictionaries(monkeypatch):
    calls = []

    async def fake_ensure_menu(**kwargs):
        calls.append(("menu", kwargs))

    async def fake_reconcile_menu_subtree(**kwargs):
        calls.append(("reconcile", kwargs))

    async def fake_ensure_role(**kwargs):
        calls.append(("role", kwargs))

    async def fake_ensure_user(**kwargs):
        calls.append(("user", kwargs))

    async def fake_safe_update_or_create(model, lookup, defaults):
        calls.append(("dictionary", model.__name__, lookup, defaults))
        return object(), True

    monkeypatch.setattr(init_helper, "ensure_menu", fake_ensure_menu)
    monkeypatch.setattr(init_helper, "reconcile_menu_subtree", fake_reconcile_menu_subtree)
    monkeypatch.setattr(init_helper, "ensure_role", fake_ensure_role)
    monkeypatch.setattr(init_helper, "ensure_user", fake_ensure_user)
    monkeypatch.setattr(init_helper, "_safe_update_or_create", fake_safe_update_or_create)

    await init_helper.apply_init_data({
        "menus": [
            {
                "menu_name": "Root",
                "route_name": "root",
                "route_path": "/root",
                "reconcile": {"menus": True, "buttons": True},
                "children": [
                    {
                        "menu_name": "Child",
                        "route_name": "root_child",
                        "route_path": "/root/child",
                        "component": "view.root_child",
                        "reconcile": False,
                        "buttons": [{"button_code": "B_ROOT_CHILD_CREATE", "button_desc": "创建"}],
                    }
                ],
            }
        ],
        "roles": [{"role_name": "Root Admin", "role_code": "R_ROOT_ADMIN"}],
        "users": [{"user_name": "Root", "password": "123456", "role_codes": ["R_ROOT_ADMIN"]}],
        "dictionaries": [{"dict_type": "color", "value": "red", "label": "红色", "order": 1}],
    })

    assert [call[0] for call in calls] == ["menu", "reconcile", "role", "user", "dictionary"]
    menu_payload = calls[0][1]
    assert "reconcile" not in menu_payload
    assert "reconcile" not in menu_payload["children"][0]
    assert calls[1][1] == {
        "root_route": "root",
        "declared_route_names": {"root_child"},
        "declared_button_codes": {"B_ROOT_CHILD_CREATE"},
    }
    assert calls[4][2] == {"dict_type": "color", "value": "red"}
    assert calls[4][3] == {"label": "红色", "order": 1}
