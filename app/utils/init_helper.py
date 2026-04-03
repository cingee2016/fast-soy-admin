"""
业务模块初始化数据的公共 API — 声明式创建/更新菜单/按钮/角色。

所有函数幂等：根据唯一键 get_or_update，声明即真实状态。

Usage (in app/business/hr/init_data.py):

    async def init():
        await ensure_menu(
            menu_name="HR管理", route_name="hr", route_path="/hr",
            icon="mdi:account-group", order=8,
            children=[
                dict(menu_name="员工管理", route_name="hr_employee",
                     route_path="/hr/employee", component="view.hr_employee", order=1),
            ],
            buttons=[
                dict(button_code="B_HR_CREATE", button_desc="创建员工"),
            ],
        )

        await ensure_role(
            role_name="部门主管", role_code="R_DEPT_MGR",
            menus=["hr", "hr_employee"],
            buttons=["B_HR_CREATE"],
            apis=[("post", "/api/v1/business/hr/employees")],
        )
"""

from __future__ import annotations

from app.core.log import log


async def ensure_menu(
    *,
    parent_route: str | None = None,
    menu_name: str,
    route_name: str,
    route_path: str,
    component: str | None = None,
    icon: str | None = None,
    icon_type: str = "1",
    menu_type: str | None = None,
    order: int = 1,
    i18n_key: str | None = None,
    children: list[dict] | None = None,
    buttons: list[dict] | None = None,
    **extra,
) -> None:
    """
    确保菜单存在且字段与声明一致（幂等，按 route_name 唯一键 get_or_update）。

    Args:
        parent_route: 父菜单的 route_name (如 "manage")，为 None 时创建顶级菜单
        menu_type: 强制指定菜单类型 ("1"=catalog, "2"=menu)，为 None 时自动推断
        children: [{"menu_name", "route_name", "route_path", "component", "order",
                     "icon", ..., "children": [...], "buttons": [...]}]
        buttons: [{"button_code", "button_desc"}] — 挂在当前菜单上。
                 传 None 表示不修改现有按钮，传 [] 表示清空按钮。
        **extra: 传递给 Menu 的额外字段，如 constant, hide_in_menu, props,
                 multi_tab, redirect。active_menu 传 route_name 字符串会自动解析。
    """
    from app.core.base_model import IconType, MenuType
    from app.system.models.admin import Button, Menu

    # 确定 parent_id
    if parent_route is None:
        parent_id = 0
    else:
        parent = await Menu.filter(route_name=parent_route).first()
        if not parent:
            log.warning(f"ensure_menu: parent '{parent_route}' not found, skip '{route_name}'")
            return
        parent_id = parent.id

    # 推断菜单类型
    if menu_type is not None:
        resolved_type = MenuType(menu_type)
    else:
        resolved_type = MenuType.catalog if children else MenuType.menu
    if parent_id == 0 and component is None and not extra.get("constant"):
        component = "layout.base"

    # 解析 active_menu (route_name -> Menu 实例)
    if "active_menu" in extra and isinstance(extra["active_menu"], str):
        active = await Menu.filter(route_name=extra["active_menu"]).first()
        extra["active_menu"] = active

    # get_or_update
    defaults = {
        "parent_id": parent_id,
        "menu_type": resolved_type,
        "menu_name": menu_name,
        "route_path": route_path,
        "component": component,
        "order": order,
        "i18n_key": i18n_key or f"route.{route_name}",
        "icon": icon,
        "icon_type": IconType(icon_type) if icon else None,
        **extra,
    }
    main_menu, created = await Menu.update_or_create(
        route_name=route_name,
        defaults=defaults,
    )

    if created:
        log.info(f"ensure_menu: created '{route_name}'" + (f" under '{parent_route}'" if parent_route else " as top-level"))
    else:
        log.info(f"ensure_menu: updated '{route_name}'")

    # 同步按钮（None=不动，[]=清空，[...]=替换）
    if buttons is not None:
        await main_menu.by_menu_buttons.clear()
        for btn in buttons:
            btn_obj, _ = await Button.update_or_create(
                button_code=btn["button_code"],
                defaults={"button_desc": btn.get("button_desc", "")},
            )
            await main_menu.by_menu_buttons.add(btn_obj)

    # 递归处理子菜单
    for child in children or []:
        child_buttons = child.get("buttons")
        child_children = child.get("children")
        child_extra = {k: v for k, v in child.items() if k not in ("menu_name", "route_name", "route_path", "component", "order", "icon", "icon_type", "i18n_key", "menu_type", "buttons", "children")}
        await ensure_menu(
            parent_route=route_name,
            menu_name=child["menu_name"],
            route_name=child["route_name"],
            route_path=child["route_path"],
            component=child.get("component"),
            icon=child.get("icon"),
            icon_type=child.get("icon_type", "1"),
            menu_type=child.get("menu_type"),
            order=child.get("order", 1),
            i18n_key=child.get("i18n_key"),
            children=child_children,
            buttons=child_buttons,
            **child_extra,
        )


async def ensure_role(
    *,
    role_name: str,
    role_code: str,
    role_desc: str = "",
    home_route: str = "home",
    menus: list[str] | None = None,
    buttons: list[str] | None = None,
    apis: list[tuple[str, str]] | None = None,
) -> None:
    """
    确保角色存在且字段/权限与声明一致（幂等，按 role_code 唯一键 get_or_update）。

    关系同步语义：None=不修改，[]=清空，[...]=替换为声明的集合。

    Args:
        menus: route_name 列表
        buttons: button_code 列表
        apis: [(method, path), ...] 列表
    """
    from app.system.models.admin import Api, Button, Menu, Role

    home_menu = await Menu.filter(route_name=home_route).first()
    role, created = await Role.update_or_create(
        role_code=role_code,
        defaults={
            "role_name": role_name,
            "role_desc": role_desc,
            "by_role_home_id": home_menu.id if home_menu else 1,
        },
    )

    # 同步菜单
    if menus is not None:
        await role.by_role_menus.clear()
        for rn in menus:
            menu = await Menu.filter(route_name=rn).first()
            if menu:
                await role.by_role_menus.add(menu)

    # 同步按钮
    if buttons is not None:
        await role.by_role_buttons.clear()
        for code in buttons:
            btn = await Button.filter(button_code=code).first()
            if btn:
                await role.by_role_buttons.add(btn)

    # 同步 API
    if apis is not None:
        await role.by_role_apis.clear()
        for method, path in apis:
            api = await Api.filter(api_method=method, api_path=path).first()
            if api:
                await role.by_role_apis.add(api)

    log.info(f"ensure_role: {'created' if created else 'updated'} role '{role_code}'")
