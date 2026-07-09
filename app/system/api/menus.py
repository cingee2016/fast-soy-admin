from fastapi import Query
from tortoise.expressions import Q

from app.core.autodiscover import discover_business_module_names
from app.core.base_schema import Fail, Success, SuccessExtra
from app.core.code import Code
from app.core.router import CRUDRouter, SearchFieldConfig
from app.core.sqids import encode_id
from app.core.types import SqidPath
from app.system.controllers import menu_controller
from app.system.models import IconType, Menu, MenuType
from app.system.schemas.admin import MenuCreate, MenuSearch, MenuUpdate

# 标准 CRUD：get, delete, batch_delete（默认启用）
# list/create/update 使用 override 注入树结构和按钮关联
crud = CRUDRouter(
    prefix="/menus",
    controller=menu_controller,
    create_schema=MenuCreate,
    update_schema=MenuUpdate,
    list_schema=MenuSearch,
    search_fields=SearchFieldConfig(
        contains_fields=["menu_name"],
        exact_fields=["menu_type", "status_type"],
    ),
    summary_prefix="菜单",
    enable_routes={"list", "create", "update", "delete", "batch_delete"},
)
router = crud.router


def _dump_menu_for_write(obj_in: MenuCreate | MenuUpdate, exclude: set[str] | None = None, keep_none: bool = False) -> dict:
    obj_dict = obj_in.model_dump(exclude_unset=True, exclude_none=not keep_none, exclude=exclude)
    if "parent_id" in obj_in.model_fields_set and obj_in.parent_id is None:
        obj_dict["parent_id"] = 0
    return obj_dict


def _get_hidden_menu_effective_parent(menu: Menu, menus: list[Menu], menu_ids: set[int]) -> int:
    if menu.active_menu_id and menu.active_menu_id in menu_ids and menu.parent_id != menu.active_menu_id:
        return menu.active_menu_id

    route_name = menu.route_name or ""
    route_name_candidates = [
        item
        for item in menus
        if item.id != menu.id and not item.hide_in_menu and item.id in menu_ids and item.route_name and (route_name.startswith(f"{item.route_name}_") or route_name.startswith(f"{item.route_name}-"))
    ]
    if route_name_candidates:
        return max(route_name_candidates, key=lambda item: len(item.route_name or "")).id

    route_path = (menu.route_path or "").rstrip("/")
    if not route_path:
        return menu.parent_id

    candidates = [
        item for item in menus if item.id != menu.id and not item.hide_in_menu and item.id in menu_ids and item.route_path and route_path.startswith(f"{(item.route_path or '').rstrip('/')}/")
    ]
    if not candidates:
        return menu.parent_id

    return max(candidates, key=lambda item: len(item.route_path or "")).id


def _get_effective_parent_ids(menus: list[Menu], include_hidden: bool = False) -> dict[int, int]:
    menu_ids = {menu.id for menu in menus}
    effective_parent_ids: dict[int, int] = {}

    for menu in menus:
        parent_id = menu.parent_id
        if include_hidden and menu.hide_in_menu:
            parent_id = _get_hidden_menu_effective_parent(menu, menus, menu_ids)
        effective_parent_ids[menu.id] = parent_id

    return effective_parent_ids


async def build_menu_tree(
    menus: list[Menu],
    parent_id: int = 0,
    simple: bool = False,
    effective_parent_ids: dict[int, int] | None = None,
) -> list[dict]:
    """递归生成菜单树"""
    tree = []
    for menu in menus:
        effective_parent_id = effective_parent_ids.get(menu.id, menu.parent_id) if effective_parent_ids else menu.parent_id
        if effective_parent_id == parent_id:
            node_key = f"menu:{encode_id(menu.id)}"
            children = await build_menu_tree(menus, menu.id, simple, effective_parent_ids)
            if simple:
                if menu.menu_type == MenuType.catalog and not children:
                    continue
                is_parent = menu.menu_type == MenuType.catalog or bool(children)
                menu_dict = {
                    "key": node_key,
                    "label": menu.menu_name,
                    "isParent": is_parent,
                    "resourceId": None if is_parent else encode_id(menu.id),
                    "routeName": menu.route_name,
                    "meta": {"hidden": menu.hide_in_menu},
                }
            else:
                menu_dict = await menu.to_dict()
                if menu_dict.get("parentId") == 0:
                    menu_dict["parentId"] = None
                if menu.icon_type == IconType.local:
                    menu_dict["localIcon"] = menu.icon
                    menu_dict.pop("icon")
                menu_dict["buttons"] = [await button.to_dict() for button in await menu.by_menu_buttons]
            if children:
                menu_dict["children"] = children
            tree.append(menu_dict)
    return tree


# ---- 覆盖 list：返回树结构 ----


async def _collect_business_menu_ids() -> set[int]:
    """收集所有挂在业务模块根路由下的菜单 ID（含子树）。"""
    biz_names = discover_business_module_names()
    if not biz_names:
        return set()
    roots = await Menu.filter(parent_id=0, route_name__in=biz_names).only("id")
    if not roots:
        return set()
    collected: set[int] = {m.id for m in roots}
    frontier: set[int] = set(collected)
    while frontier:
        children = await Menu.filter(parent_id__in=list(frontier)).only("id")
        new_ids = {c.id for c in children} - collected
        if not new_ids:
            break
        collected |= new_ids
        frontier = new_ids
    return collected


@crud.override("list")
async def _list_menus(obj_in: MenuSearch):
    # 三个开关语义：菜单属于某类别时，只要对应开关开启即显示；
    # 不属于任何特殊类别的"普通菜单"始终显示。
    biz_ids = list(await _collect_business_menu_ids())

    # 普通菜单：非常量、非隐藏、非业务
    regular = Q(constant=False) & Q(hide_in_menu=False)
    if biz_ids:
        regular &= ~Q(id__in=biz_ids)
    combined = regular

    if obj_in.include_constant:
        combined |= Q(constant=True)
    if obj_in.include_hidden:
        combined |= Q(hide_in_menu=True)
    if obj_in.include_business and biz_ids:
        combined |= Q(id__in=biz_ids)

    # 菜单为树结构，按扁平记录分页会让子树看不到；此处一次性返回全部匹配项
    menus = await Menu.filter(combined).order_by("id").prefetch_related("by_menu_buttons")
    menu_tree = await build_menu_tree(menus, simple=False)
    total = len(menus)
    return SuccessExtra(data={"records": menu_tree}, total=total, current=obj_in.current or 1, size=obj_in.size or 1)


# ---- 覆盖 create/update：按钮关联 + active_menu 处理 ----


@crud.override("create")
async def _create_menu(menu_in: MenuCreate):
    if await menu_controller.exists(route_path=menu_in.route_path):
        return Fail(code=Code.DUPLICATE_MENU_ROUTE, msg=f"路由路径 {menu_in.route_path} 已存在")

    if menu_in.active_menu:
        active_menu_obj = await menu_controller.get(menu_name=menu_in.active_menu)
        obj_dict = _dump_menu_for_write(menu_in, exclude={"by_menu_buttons", "active_menu"})
        obj_dict["active_menu_id"] = active_menu_obj.id
        new_menu = await menu_controller.create(obj_in=obj_dict)
    else:
        new_menu = await menu_controller.create(obj_in=_dump_menu_for_write(menu_in, exclude={"by_menu_buttons"}))
    if new_menu and "by_menu_buttons" in menu_in.model_fields_set:
        await menu_controller.update_buttons_by_code(new_menu, menu_in.by_menu_buttons)
    return Success(msg="创建成功", data={"createdId": encode_id(new_menu.id)})


@crud.override("update")
async def _update_menu(item_id: SqidPath, obj_in: MenuUpdate):
    obj_dict = _dump_menu_for_write(obj_in, exclude={"by_menu_buttons", "active_menu"}, keep_none=True)
    if "active_menu" in obj_in.model_fields_set:
        if obj_in.active_menu:
            active_menu_obj = await menu_controller.get(menu_name=obj_in.active_menu)
            obj_dict["active_menu_id"] = active_menu_obj.id
        else:
            obj_dict["active_menu_id"] = None

    menu_obj = await menu_controller.update(id=item_id, obj_in=obj_dict)
    if menu_obj and "by_menu_buttons" in obj_in.model_fields_set:
        await menu_controller.update_buttons_by_code(menu_obj, obj_in.by_menu_buttons)
    return Success(msg="更新成功", data={"updatedId": encode_id(item_id)})


# ---- 扩展：菜单树（简化）/ 页面列表 / 按钮树 ----


@router.get("/menus/tree", summary="查看菜单树")
async def _(include_hidden: bool = Query(False, alias="includeHidden")):
    q = Q(constant=False)
    if not include_hidden:
        q &= Q(hide_in_menu=False)
    menus = await Menu.filter(q).order_by("id")
    effective_parent_ids = _get_effective_parent_ids(menus, include_hidden=include_hidden)
    return Success(data=await build_menu_tree(menus, simple=True, effective_parent_ids=effective_parent_ids))


@router.get("/menus/pages", summary="查看一级菜单")
async def _():
    menus = await Menu.filter(parent_id=0, constant=False)
    return Success(data=[{"key": m.menu_name, "value": encode_id(m.id)} for m in menus])


@router.get("/menus/buttons/tree", summary="查看菜单按钮树")
async def _():
    all_menus = await Menu.filter(constant=False)
    if not all_menus:
        return Success(data=[])

    menu_button_map: dict[int, list[dict]] = {}
    for menu in all_menus:
        buttons = await menu.by_menu_buttons.all()
        if buttons:
            menu_button_map[menu.id] = [
                {
                    "key": f"button:{encode_id(b.id)}",
                    "label": b.button_desc,
                    "isParent": False,
                    "resourceId": encode_id(b.id),
                }
                for b in buttons
            ]

    if not menu_button_map:
        return Success(data=[])

    menu_map = {m.id: m for m in all_menus}
    needed_ids: set[int] = set()
    for mid in menu_button_map:
        cur = mid
        while cur in menu_map and cur not in needed_ids:
            needed_ids.add(cur)
            cur = menu_map[cur].parent_id

    menu_objs = [m for m in all_menus if m.id in needed_ids]

    def build_tree(parent_id: int = 0) -> list[dict]:
        result = []
        for menu in menu_objs:
            if menu.parent_id == parent_id:
                children = build_tree(menu.id)
                btns = menu_button_map.get(menu.id, [])
                combined = children + btns
                if combined:
                    node: dict = {
                        "key": f"menu:{encode_id(menu.id)}",
                        "label": menu.menu_name,
                        "isParent": True,
                        "resourceId": None,
                    }
                    node["children"] = combined
                    result.append(node)
        return result

    return Success(data=build_tree())
