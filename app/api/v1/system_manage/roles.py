from fastapi import Query, Request
from tortoise.expressions import Q

from app.controllers import role_controller
from app.controllers.menu import menu_controller
from app.core.cache import load_role_permissions
from app.core.code import Code
from app.core.router import CRUDRouter, SearchFieldConfig
from app.models.system import Api, Button, Role
from app.schemas.admin import RoleCreate, RoleUpdate, RoleUpdateAuthrization
from app.schemas.base import Fail, Success, SuccessExtra

# 标准 CRUD 路由：get, delete, batch_delete
crud = CRUDRouter(
    prefix="/roles",
    controller=role_controller,
    create_schema=RoleCreate,
    update_schema=RoleUpdate,
    search_fields=SearchFieldConfig(
        contains_fields=["role_name", "role_code", "status"],
    ),
    summary_prefix="角色",
    list_order=["id"],
    enable_routes={"get", "delete", "batch_delete"},
)
router = crud.router


# ---- 覆盖默认的 create/update（需要额外校验） ----


@router.post("/roles", summary="创建角色")
async def _(role_in: RoleCreate, request: Request):
    if await role_controller.exists(role_code=role_in.role_code):
        return Fail(code=Code.DUPLICATE_RESOURCE, msg="The role with this code already exists in the system.")

    new_role = await role_controller.create(obj_in=role_in)
    # 新角色写入 Redis
    await load_role_permissions(request.app.state.redis, role_code=new_role.role_code)
    return Success(msg="Created Successfully", data={"created_id": new_role.id})


@router.patch("/roles/{role_id}", summary="更新角色")
async def _(role_id: int, role_in: RoleUpdate, request: Request):
    role_obj = await role_controller.update(id=role_id, obj_in=role_in)
    await load_role_permissions(request.app.state.redis, role_code=role_obj.role_code)
    return Success(msg="Updated Successfully", data={"updated_id": role_id})


# ---- 覆盖默认的 list（需要搜索参数） ----


@router.get("/roles", summary="查看角色列表")
async def _(
    current: int = Query(1, description="页码"),
    size: int = Query(10, description="每页数量"),
    roleName: str = Query(None, description="角色名称"),
    roleCode: str = Query(None, description="角色编码"),
    status: str = Query(None, description="用户状态"),
):
    q = Q()
    if roleName:
        q &= Q(role_name__contains=roleName)
    if roleCode:
        q &= Q(role_code__contains=roleCode)
    if status:
        q &= Q(status__contains=status)

    total, role_objs = await role_controller.list(page=current, page_size=size, search=q, order=["id"])
    records = [await role_obj.to_dict() for role_obj in role_objs]
    data = {"records": records}
    return SuccessExtra(data=data, total=total, current=current, size=size)


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
    if role_in.by_role_home_id:
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

        # 角色菜单变动，刷新 Redis
        await load_role_permissions(request.app.state.redis, role_code=role_obj.role_code)

    return Success(msg="Updated Successfully", data={"by_role_menu_ids": role_in.by_role_menu_ids, "by_role_home_id": role_in.by_role_home_id})


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
        await role_obj.by_role_buttons.clear()
        for button_id in role_in.by_role_button_ids:
            button_obj = await Button.get(id=button_id)
            await role_obj.by_role_buttons.add(button_obj)

    # 角色按钮变动，刷新 Redis
    await load_role_permissions(request.app.state.redis, role_code=role_obj.role_code)
    return Success(msg="Updated Successfully", data={"by_role_button_ids": role_in.by_role_button_ids})


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
        await role_obj.by_role_apis.clear()
        for api_id in role_in.by_role_api_ids:
            api_obj = await Api.get(id=api_id)
            await role_obj.by_role_apis.add(api_obj)

    # 角色 API 变动，刷新 Redis
    await load_role_permissions(request.app.state.redis, role_code=role_obj.role_code)
    return Success(msg="Updated Successfully", data={"by_role_api_ids": role_in.by_role_api_ids})
