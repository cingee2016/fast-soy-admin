"""
系统初始化辅助服务。

这里承载菜单、角色、种子用户等 system 领域的初始化编排逻辑。

多进程安全说明：
    启动时通过 Redis 分布式锁保证仅一个 worker 执行 init，但仍在
    update_or_create 处增加 IntegrityError 重试，以应对极端时序场景。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

from tortoise.models import Model

from app.core.exceptions import IntegrityError
from app.core.log import log

if TYPE_CHECKING:
    from app.system.models import User

_M = TypeVar("_M", bound=Model)


async def _safe_update_or_create(model: type[_M], lookup: dict[str, Any], defaults: dict[str, Any]) -> tuple[_M, bool]:
    """
    对 update_or_create 的安全封装，处理并发 UNIQUE 冲突。

    当两个协程/进程同时对同一唯一键执行 get→create 时，
    后者会抛 IntegrityError；此处捕获后回退为 update。
    """
    try:
        return await model.update_or_create(defaults=defaults, **lookup)  # type: ignore[return-value]
    except IntegrityError:
        log.debug(f"_safe_update_or_create: IntegrityError on {model.__name__} {lookup}, retrying as update")
        await model.filter(**lookup).update(**defaults)
        instance = await model.get(**lookup)
        return instance, False


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

    if parent_route is None:
        parent_id = 0
    else:
        parent = await Menu.filter(route_name=parent_route).first()
        if not parent:
            log.warning(f"ensure_menu: parent '{parent_route}' not found, skip '{route_name}'")
            return
        parent_id = parent.id

    if menu_type is not None:
        resolved_type = MenuType(menu_type)
    else:
        resolved_type = MenuType.catalog if children else MenuType.menu
    if parent_id == 0 and component is None and not extra.get("constant"):
        component = "layout.base"

    if "active_menu" in extra and isinstance(extra["active_menu"], str):
        active = await Menu.filter(route_name=extra["active_menu"]).first()
        extra["active_menu"] = active

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
    main_menu, created = await _safe_update_or_create(Menu, {"route_name": route_name}, defaults)

    if created:
        log.info(f"ensure_menu: created '{route_name}'" + (f" under '{parent_route}'" if parent_route else " as top-level"))
    else:
        log.info(f"ensure_menu: updated '{route_name}'")

    if buttons is not None:
        await main_menu.by_menu_buttons.clear()  # type: ignore[attr-defined]
        for btn in buttons:
            btn_obj, _ = await _safe_update_or_create(Button, {"button_code": btn["button_code"]}, {"button_desc": btn.get("button_desc", "")})
            await main_menu.by_menu_buttons.add(btn_obj)  # type: ignore[attr-defined]

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
    role, created = await _safe_update_or_create(
        Role,
        {"role_code": role_code},
        {
            "role_name": role_name,
            "role_desc": role_desc,
            "by_role_home_id": home_menu.id if home_menu else 1,
        },
    )

    if menus is not None:
        await role.by_role_menus.clear()  # type: ignore[attr-defined]
        for rn in menus:
            menu = await Menu.filter(route_name=rn).first()
            if menu:
                await role.by_role_menus.add(menu)  # type: ignore[attr-defined]

    if buttons is not None:
        await role.by_role_buttons.clear()  # type: ignore[attr-defined]
        for code in buttons:
            btn = await Button.filter(button_code=code).first()
            if btn:
                await role.by_role_buttons.add(btn)  # type: ignore[attr-defined]

    if apis is not None:
        await role.by_role_apis.clear()  # type: ignore[attr-defined]
        for method, path in apis:
            api = await Api.filter(api_method=method, api_path=path).first()
            if api:
                await role.by_role_apis.add(api)  # type: ignore[attr-defined]

    log.info(f"ensure_role: {'created' if created else 'updated'} role '{role_code}'")


async def ensure_user(
    *,
    user_name: str,
    password: str,
    role_codes: list[str],
    user_email: str | None = None,
    nick_name: str | None = None,
    user_phone: str | None = None,
    user_gender: str | None = None,
    must_change_password: bool = False,
    reset_password: bool = False,
) -> "User":
    """
    确保用户存在且角色与声明一致。

    语义：
    - 首次不存在时创建
    - 已存在时同步基础资料和角色
    - 默认不重置密码，避免每次启动覆盖已有账号密码
    """
    from app.core.base_model import GenderType
    from app.system.controllers.user import user_controller
    from app.system.models import User
    from app.system.security import get_password_hash

    base_payload = {
        "nick_name": nick_name or user_name,
        "must_change_password": must_change_password,
    }
    if user_email is not None:
        base_payload["user_email"] = user_email
    if user_phone is not None:
        base_payload["user_phone"] = user_phone
    if user_gender is not None:
        base_payload["user_gender"] = user_gender

    user = await User.filter(user_name=user_name).first()
    if user:
        payload = base_payload.copy()
        if reset_password:
            payload["password"] = get_password_hash(password)
        await User.filter(id=user.id).update(**payload)
        user = await User.get(id=user.id)
    else:
        payload = base_payload.copy()
        payload.setdefault("user_gender", GenderType.unknow)
        try:
            user = await User.create(
                user_name=user_name,
                password=get_password_hash(password),
                **payload,
            )
        except IntegrityError:
            # 并发进程已创建该用户，回退为更新
            user = await User.get(user_name=user_name)
            await User.filter(id=user.id).update(**base_payload)

    await user_controller.update_roles_by_code(user, role_codes)
    log.info(f"ensure_user: synced user '{user_name}'")
    return user
