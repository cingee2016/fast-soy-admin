from app.core.constants import SUPER_ADMIN_ROLE
from app.core.data_scope import DataScopeType
from app.system.models import Button, Menu, Role
from app.system.models.dictionary import Dictionary
from app.system.services import ensure_menu, ensure_role, ensure_user
from app.system.services.init_helper import _safe_update_or_create


def _crud_apis(resource: str, *, with_tree: bool = False) -> list[tuple[str, str]]:
    """生成一组 CRUDRouter 标准路由的 (method, path)（不含 GET 详情，前端均无调用）。"""
    base = f"/api/v1/system-manage/{resource}"
    apis = [
        ("post", f"{base}/search"),
        ("post", base),
        ("patch", f"{base}/{{item_id}}"),
        ("delete", f"{base}/{{item_id}}"),
        ("delete", base),
    ]
    if with_tree:
        apis.append(("get", f"{base}/tree"))
    return apis


SLIM_ROUTE_NAMES = {
    "login",
    "403",
    "404",
    "500",
    "home",
    "manage",
    "manage_api",
    "manage_user",
    "manage_role",
    "manage_menu",
    "manage_user-detail",
    "manage_radar",
    "manage_radar_overview",
    "manage_radar_requests",
    "manage_radar_queries",
    "manage_radar_exceptions",
    "manage_radar_monitor",
}


SYSTEM_ROLE_SEEDS = [
    {
        "role_name": "管理员",
        "role_code": "R_ADMIN",
        "role_desc": "系统管理员，可维护用户/角色/菜单/API/字典/监控",
        "home_route": "home",
        "data_scope": DataScopeType.all,
        "menus": [
            "home",
            "manage",
            "manage_user",
            "manage_user-detail",
            "manage_role",
            "manage_menu",
            "manage_api",
            "manage_radar",
            "manage_radar_overview",
            "manage_radar_requests",
            "manage_radar_queries",
            "manage_radar_exceptions",
            "manage_radar_monitor",
        ],
        "buttons": [],
        "apis": [
            # 用户
            *_crud_apis("users"),
            ("post", "/api/v1/system-manage/users/{user_id}/offline"),
            ("post", "/api/v1/system-manage/users/batch-offline"),
            # 角色
            *_crud_apis("roles"),
            ("get", "/api/v1/system-manage/roles/{role_id}/menus"),
            ("patch", "/api/v1/system-manage/roles/{role_id}/menus"),
            ("get", "/api/v1/system-manage/roles/{role_id}/buttons"),
            ("patch", "/api/v1/system-manage/roles/{role_id}/buttons"),
            ("get", "/api/v1/system-manage/roles/{role_id}/apis"),
            ("patch", "/api/v1/system-manage/roles/{role_id}/apis"),
            # 菜单
            *_crud_apis("menus"),
            ("get", "/api/v1/system-manage/menus/tree"),
            ("get", "/api/v1/system-manage/menus/pages"),
            ("get", "/api/v1/system-manage/menus/buttons/tree"),
            # API（资源由 refresh_api_list 全量对账，UI 仅只读）
            ("post", "/api/v1/system-manage/apis/search"),
            ("get", "/api/v1/system-manage/apis/tree"),
            ("get", "/api/v1/system-manage/apis/tags"),
            # 字典
            ("get", "/api/v1/system-manage/dictionaries/{dict_type}/options"),
        ],
    },
    {
        "role_name": "普通用户",
        "role_code": "R_USER",
        "role_desc": "基础用户，仅可访问首页",
        "home_route": "home",
        "data_scope": DataScopeType.self_,
        "menus": ["home"],
    },
]

SYSTEM_USER_SEEDS = [
    {"user_name": "Soybean", "user_email": "admin@admin.com", "password": "123456", "role_codes": [SUPER_ADMIN_ROLE]},
    {"user_name": "Super", "user_email": "admin1@admin.com", "password": "123456", "role_codes": [SUPER_ADMIN_ROLE]},
    {"user_name": "Admin", "user_email": "admin2@admin.com", "password": "123456", "role_codes": ["R_ADMIN"]},
    {"user_name": "User", "user_email": "user@user.com", "password": "123456", "role_codes": ["R_USER"]},
]


async def init_menus():
    # ---- 常量路由（不受权限控制） ----
    for name, path, comp, order, extra in [
        ("login", "/login", "layout.blank$view.login", 1, {"props": True}),
        ("403", "/403", "layout.blank$view.403", 2, {}),
        ("404", "/404", "layout.blank$view.404", 3, {}),
        ("500", "/500", "layout.blank$view.500", 4, {}),
    ]:
        await ensure_menu(
            menu_name=name,
            route_name=name,
            route_path=path,
            component=comp,
            order=order,
            menu_type="1",
            constant=True,
            hide_in_menu=True,
            **extra,
        )

    # ---- 首页 ----
    await ensure_menu(
        menu_name="首页",
        route_name="home",
        route_path="/home",
        component="layout.base$view.home",
        order=1,
        icon="mdi:monitor-dashboard",
    )

    # ---- 系统管理 ----
    await ensure_menu(
        menu_name="系统管理",
        route_name="manage",
        route_path="/manage",
        order=1,
        icon="carbon:cloud-service-management",
        children=[
            dict(
                menu_name="API管理",
                route_name="manage_api",
                route_path="/manage/api",
                component="view.manage_api",
                order=1,
                icon="ant-design:api-outlined",
            ),
            dict(menu_name="用户管理", route_name="manage_user", route_path="/manage/user", component="view.manage_user", order=2, icon="ic:round-manage-accounts"),
            dict(menu_name="角色管理", route_name="manage_role", route_path="/manage/role", component="view.manage_role", order=3, icon="carbon:user-role"),
            dict(menu_name="菜单管理", route_name="manage_menu", route_path="/manage/menu", component="view.manage_menu", order=4, icon="material-symbols:route"),
            dict(menu_name="用户详情", route_name="manage_user-detail", route_path="/manage/user-detail/:id", component="view.manage_user-detail", order=5, hide_in_menu=True),
            dict(
                menu_name="性能监控",
                route_name="manage_radar",
                route_path="/manage/radar",
                order=7,
                icon="mdi:radar",
                menu_type="1",
                children=[
                    dict(menu_name="仪表板", route_name="manage_radar_overview", route_path="/manage/radar/overview", component="view.manage_radar_overview", order=1, icon="mdi:chart-box-outline"),
                    dict(menu_name="请求列表", route_name="manage_radar_requests", route_path="/manage/radar/requests", component="view.manage_radar_requests", order=2, icon="mdi:swap-horizontal"),
                    dict(menu_name="SQL查询", route_name="manage_radar_queries", route_path="/manage/radar/queries", component="view.manage_radar_queries", order=3, icon="mdi:database-search"),
                    dict(menu_name="异常列表", route_name="manage_radar_exceptions", route_path="/manage/radar/exceptions", component="view.manage_radar_exceptions", order=4, icon="mdi:bug-outline"),
                    dict(menu_name="系统监控", route_name="manage_radar_monitor", route_path="/manage/radar/monitor", component="view.manage_radar_monitor", order=5, icon="mdi:monitor-dashboard"),
                ],
            ),
        ],
    )

    await _prune_slim_menus()


async def _prune_slim_menus() -> None:
    """删除 slim 分支不再声明的旧示例菜单，并迁移旧角色首页。"""
    keep_menus = await Menu.filter(route_name__in=SLIM_ROUTE_NAMES).only("id", "route_name")
    keep_ids = {m.id for m in keep_menus}
    home_menu = next((m for m in keep_menus if m.route_name == "home"), None)
    if not keep_ids or home_menu is None:
        return

    await Role.exclude(by_role_home_id__in=list(keep_ids)).update(by_role_home_id=home_menu.id)

    stale_menus = await Menu.exclude(route_name__in=SLIM_ROUTE_NAMES).only("id")
    stale_ids = [m.id for m in stale_menus]
    if stale_ids:
        await Menu.filter(id__in=stale_ids).update(active_menu_id=None)
        for menu_obj in await Menu.filter(id__in=stale_ids).order_by("-id"):
            await menu_obj.delete()

    for button_obj in await Button.all():
        if await button_obj.by_button_menus.all():
            continue
        await button_obj.delete()


async def _ensure_super_role() -> None:
    """同步超级管理员角色到最新菜单和按钮集合"""
    role_home_menu = await Menu.get(route_name="home")
    super_role, _ = await _safe_update_or_create(
        Role,
        {"role_code": SUPER_ADMIN_ROLE},
        {
            "role_name": "超级管理员",
            "role_desc": "超级管理员",
            "by_role_home": role_home_menu,
        },
    )

    await super_role.by_role_menus.clear()  # type: ignore[attr-defined]
    for menu_obj in await Menu.filter(constant=False):
        await super_role.by_role_menus.add(menu_obj)  # type: ignore[attr-defined]

    await super_role.by_role_buttons.clear()  # type: ignore[attr-defined]
    for button_obj in await Button.all():
        await super_role.by_role_buttons.add(button_obj)  # type: ignore[attr-defined]


DICTIONARY_SEEDS = [
    # slim 分支不内置业务示例字典；业务模块可在自身 init_data 中声明。
]


async def _init_dictionaries() -> None:
    """初始化系统字典数据"""
    for seed in DICTIONARY_SEEDS:
        await _safe_update_or_create(
            Dictionary,
            {"dict_type": seed["dict_type"], "value": seed["value"]},
            {"label": seed["label"], "order": seed["order"]},
        )


async def init_users():
    await _ensure_super_role()

    for role_seed in SYSTEM_ROLE_SEEDS:
        await ensure_role(**role_seed)

    for user_seed in SYSTEM_USER_SEEDS:
        await ensure_user(**user_seed)

    await _init_dictionaries()
