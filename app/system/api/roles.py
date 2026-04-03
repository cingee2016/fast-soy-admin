from fastapi import Request
from tortoise.transactions import in_transaction

from app.core.base_schema import Fail, Success
from app.core.cache import load_role_permissions
from app.core.code import Code
from app.core.router import CRUDRouter, SearchFieldConfig
from app.system.controllers import menu_controller, role_controller
from app.system.models import Api, Button, Role
from app.system.schemas.admin import RoleCreate, RoleSearch, RoleUpdate, RoleUpdateAuthrization

# 标准 CRUD 路由：list(POST搜索), get, delete, batch_delete
crud = CRUDRouter(
    prefix="/roles",
    controller=role_controller,
    list_schema=RoleSearch,
    search_fields=SearchFieldConfig(
        contains_fields=["role_name", "role_code"],
        exact_fields=["status_type"],
    ),
    summary_prefix="角色",
    list_order=["id"],
    batch_delete_method="body",
    enable_routes={"list", "get", "delete", "batch_delete"},
)
router = crud.router


# ---- 自定义 create/update（需要刷新 Redis 缓存） ----


@router.post("/roles", summary="创建角色")
async def _(role_in: RoleCreate, request: Request):
    if await role_controller.exists(role_code=role_in.role_code):
        return Fail(code=Code.DUPLICATE_RESOURCE, msg="该角色编码已存在")

    new_role = await role_controller.create(obj_in=role_in)
    await load_role_permissions(request.app.state.redis, role_code=new_role.role_code)
    return Success(msg="创建成功", data={"created_id": new_role.id})


@router.patch("/roles/{role_id}", summary="更新角色")
async def _(role_id: int, role_in: RoleUpdate, request: Request):
    role_obj = await role_controller.update(id=role_id, obj_in=role_in)
    await load_role_permissions(request.app.state.redis, role_code=role_obj.role_code)
    return Success(msg="更新成功", data={"updated_id": role_id})


# ---- 自定义扩展接口：角色菜单/按钮/API 管理 ----


@router.get("/roles/{role_id}/menus", summary="查看角色菜单")
async def _(role_id: int):
    role_obj = await Role.get(id=role_id).prefetch_related("by_role_home")
    if role_obj.role_code == "R_SUPER":
        menu_objs = await menu_controller.model.filter(constant=False)
    else:
        menu_objs = await role_obj.by_role_menus
    data = {"byRoleHomeId": role_obj.by_role_home.id, "byRoleMenuIds": [menu_obj.id for menu_obj in menu_objs]}
    return Success(data=data)


@router.patch("/roles/{role_id}/menus", summary="更新角色菜单")
async def _(role_id: int, role_in: RoleUpdateAuthrization, request: Request):
    role_obj = await role_controller.get(id=role_id)
    if role_in.by_role_home_id:
        async with in_transaction("conn_system"):
            role_obj = await role_controller.update(id=role_id, obj_in=dict(by_role_home_id=role_in.by_role_home_id))
            if role_in.by_role_menu_ids:
                menu_objs = await menu_controller.get_by_id_list(id_list=role_in.by_role_menu_ids)
                if not menu_objs:
                    return Success(msg="获取角色菜单对象失败", code=2000)

                await role_obj.by_role_menus.clear()
                while len(menu_objs) > 0:
                    menu_obj = menu_objs.pop()
                    await role_obj.by_role_menus.add(menu_obj)
                    if menu_obj.parent_id != 0:
                        menu_objs.append(await menu_controller.get(id=menu_obj.parent_id))
            else:
                await role_obj.by_role_menus.clear()

        await load_role_permissions(request.app.state.redis, role_code=role_obj.role_code)

    return Success(msg="更新成功", data={"by_role_menu_ids": role_in.by_role_menu_ids, "by_role_home_id": role_in.by_role_home_id})


@router.get("/roles/{role_id}/buttons", summary="查看角色按钮")
async def _(role_id: int):
    role_obj = await role_controller.get(id=role_id)
    if role_obj.role_code == "R_SUPER":
        button_objs = await Button.all()
    else:
        button_objs = await role_obj.by_role_buttons

    data = {"byRoleButtonIds": [button_obj.id for button_obj in button_objs]}
    return Success(data=data)


@router.patch("/roles/{role_id}/buttons", summary="更新角色按钮")
async def _(role_id: int, role_in: RoleUpdateAuthrization, request: Request):
    role_obj = await role_controller.get(id=role_id)
    if role_in.by_role_button_ids is not None:
        async with in_transaction("conn_system"):
            await role_obj.by_role_buttons.clear()
            for button_id in role_in.by_role_button_ids:
                button_obj = await Button.get(id=button_id)
                await role_obj.by_role_buttons.add(button_obj)

    await load_role_permissions(request.app.state.redis, role_code=role_obj.role_code)
    return Success(msg="更新成功", data={"by_role_button_ids": role_in.by_role_button_ids})


@router.get("/roles/{role_id}/apis", summary="查看角色API")
async def _(role_id: int):
    role_obj = await role_controller.get(id=role_id)
    if role_obj.role_code == "R_SUPER":
        api_objs = await Api.all()
    else:
        api_objs = await role_obj.by_role_apis

    data = {"byRoleApiIds": [api_obj.id for api_obj in api_objs]}
    return Success(data=data)


@router.patch("/roles/{role_id}/apis", summary="更新角色API")
async def _(role_id: int, role_in: RoleUpdateAuthrization, request: Request):
    role_obj = await role_controller.get(id=role_id)
    if role_in.by_role_api_ids is not None:
        async with in_transaction("conn_system"):
            await role_obj.by_role_apis.clear()
            for api_id in role_in.by_role_api_ids:
                api_obj = await Api.get(id=api_id)
                await role_obj.by_role_apis.add(api_obj)

    await load_role_permissions(request.app.state.redis, role_code=role_obj.role_code)
    return Success(msg="更新成功", data={"by_role_api_ids": role_in.by_role_api_ids})
