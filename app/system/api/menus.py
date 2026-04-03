from fastapi import Query

from app.core.base_schema import Fail, Success, SuccessExtra
from app.core.code import Code
from app.core.router import CRUDRouter
from app.system.controllers import menu_controller
from app.system.models import IconType, Menu
from app.system.schemas.admin import MenuCreate, MenuUpdate

# 标准 CRUD 路由：get, delete, batch_delete
# list/create/update 需要自定义逻辑（树结构、按钮关联等）
crud = CRUDRouter(
    prefix="/menus",
    controller=menu_controller,
    summary_prefix="菜单",
    batch_delete_method="body",
    enable_routes={"get", "delete", "batch_delete"},
)
router = crud.router


# ---- 自定义 list（返回树结构） ----


async def build_menu_tree(menus: list[Menu], parent_id: int = 0, simple: bool = False) -> list[dict]:
    """递归生成菜单树"""
    tree = []
    for menu in menus:
        if menu.parent_id == parent_id:
            children = await build_menu_tree(menus, menu.id, simple)
            if simple:
                menu_dict = {"id": menu.id, "label": menu.menu_name, "pId": menu.parent_id}
            else:
                menu_dict = await menu.to_dict()
                if menu.icon_type == IconType.local:
                    menu_dict["localIcon"] = menu.icon
                    menu_dict.pop("icon")
                menu_dict["buttons"] = [await button.to_dict() for button in await menu.by_menu_buttons]
            if children:
                menu_dict["children"] = children
            tree.append(menu_dict)
    return tree


@router.get("/menus", summary="查看用户菜单")
async def _(current: int = Query(1, description="页码"), size: int = Query(100, description="每页数量")):
    total, menus = await menu_controller.list(page=current, page_size=size, order=["id"], prefetch_related=["by_menu_buttons"])
    menu_tree = await build_menu_tree(menus, simple=False)
    data = {"records": menu_tree}
    return SuccessExtra(data=data, total=total, current=current, size=size)


@router.get("/menus/tree/", summary="查看菜单树")
async def _():
    menus = await Menu.filter(constant=False)
    menu_tree = await build_menu_tree(menus, simple=True)
    return Success(data=menu_tree)


# ---- 自定义 create/update（按钮关联、active_menu 处理） ----


@router.post("/menus", summary="创建菜单")
async def _(menu_in: MenuCreate):
    is_exist = await menu_controller.exists(route_path=menu_in.route_path)
    if is_exist:
        return Fail(code=Code.DUPLICATE_RESOURCE, msg=f"路由路径 {menu_in.route_path} 已存在")

    if menu_in.active_menu:
        menu_in.active_menu = await menu_controller.get(menu_name=menu_in.active_menu)

    new_menu = await menu_controller.create(obj_in=menu_in, exclude={"buttons"})
    if new_menu and menu_in.by_menu_buttons:
        await menu_controller.update_buttons_by_code(new_menu, menu_in.by_menu_buttons)
    return Success(msg="创建成功", data={"created_id": new_menu.id})


@router.patch("/menus/{menu_id}", summary="更新菜单")
async def _(menu_id: int, menu_in: MenuUpdate):
    menu_obj = await menu_controller.update(id=menu_id, obj_in=menu_in, exclude={"buttons"})
    if menu_obj and menu_in.by_menu_buttons:
        await menu_controller.update_buttons_by_code(menu_obj, menu_in.by_menu_buttons)
    return Success(msg="更新成功", data={"updated_id": menu_id})


# ---- 自定义扩展接口 ----


@router.get("/menus/pages/", summary="查看一级菜单")
async def _():
    menus = await Menu.filter(parent_id=0, constant=False)
    data = [{"key": menu.menu_name, "value": menu.id} for menu in menus]
    return Success(data=data)


@router.get("/menus/buttons/tree/", summary="查看菜单按钮树")
async def _():
    all_menus = await Menu.filter(constant=False)
    if not all_menus:
        return Success(data=[])

    # 为每个菜单单独查询按钮，构建 menu_id -> buttons 映射
    menu_button_map: dict[int, list[dict]] = {}
    for menu in all_menus:
        buttons = await menu.by_menu_buttons.all()
        if buttons:
            menu_button_map[menu.id] = [{"id": b.id, "label": b.button_code, "pId": menu.id} for b in buttons]

    if not menu_button_map:
        return Success(data=[])

    # 收集有按钮的菜单及其所有祖先
    menu_map = {m.id: m for m in all_menus}
    needed_ids: set[int] = set()
    for mid in menu_button_map:
        cur = mid
        while cur in menu_map and cur not in needed_ids:
            needed_ids.add(cur)
            cur = menu_map[cur].parent_id

    menu_objs = [m for m in all_menus if m.id in needed_ids]

    # 同步构建树（按钮数据已预取）
    def build_tree(parent_id: int = 0) -> list[dict]:
        result = []
        for menu in menu_objs:
            if menu.parent_id == parent_id:
                children = build_tree(menu.id)
                btns = menu_button_map.get(menu.id, [])
                node: dict = {"id": f"parent${menu.id}", "label": menu.menu_name, "pId": menu.parent_id}
                combined = children + btns
                if combined:
                    node["children"] = combined
                result.append(node)
        return result

    return Success(data=build_tree())
