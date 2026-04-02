from fastapi import Request
from tortoise.expressions import Q
from tortoise.transactions import in_transaction

from app.controllers.user import user_controller
from app.core.code import Code
from app.core.router import CRUDRouter
from app.models.system import User
from app.radar.developer import radar_log
from app.schemas.base import CommonIds, Fail, Success, SuccessExtra
from app.schemas.users import UserCreate, UserSearch, UserUpdate

# 标准 CRUD 路由：get, delete
# list/create/update/batch_delete 需要自定义逻辑
crud = CRUDRouter(
    prefix="/users",
    controller=user_controller,
    summary_prefix="用户",
    exclude_fields=["password"],
    enable_routes={"get"},
)
router = crud.router


# ---- 自定义 list（需要 role 关联查询） ----


@router.post("/users/all/", summary="查看用户列表")
async def _(obj_in: UserSearch):
    q = user_controller.build_search(
        obj_in,
        contains_fields=["user_name", "nick_name", "user_phone", "user_email"],
        exact_fields=["user_gender", "status_type"],
    )
    if obj_in.by_user_role_code_list:
        q &= Q(by_user_roles__role_code__in=obj_in.by_user_role_code_list)

    total, user_objs = await user_controller.list(page=obj_in.current, page_size=obj_in.size, search=q, order=["id"])
    records = []
    for user_obj in user_objs:
        record = await user_obj.to_dict(exclude_fields=["password"])
        await user_obj.fetch_related("by_user_roles")
        user_role_code_list = [by_user_role.role_code for by_user_role in user_obj.by_user_roles]
        record.update({"byUserRoleCodeList": user_role_code_list})
        records.append(record)
    data = {"records": records}

    return SuccessExtra(data=data, total=total, current=obj_in.current, size=obj_in.size)


# ---- 自定义 create/update（密码哈希、角色关联） ----


@router.post("/users", summary="创建用户")
async def _(user_in: UserCreate):
    if not user_in.user_email:
        return Fail(code=Code.DUPLICATE_RESOURCE, msg="This email is invalid.")

    user_obj = await user_controller.get_by_email(user_in.user_email)
    if user_obj:
        return Fail(code=Code.DUPLICATE_RESOURCE, msg="The user with this email already exists in the system.")

    if not user_in.by_user_role_code_list:
        return Fail(code=Code.DUPLICATE_RESOURCE, msg="The user must have at least one role that exists.")

    async with in_transaction("conn_system"):
        new_user = await user_controller.create(obj_in=user_in)
        await user_controller.update_roles_by_code(new_user, user_in.by_user_role_code_list)

    radar_log("创建用户", data={"targetUserId": new_user.id, "userName": user_in.user_name, "email": user_in.user_email, "roles": user_in.by_user_role_code_list})
    return Success(msg="Created Successfully", data={"created_id": new_user.id})


@router.patch("/users/{user_id}", summary="更新用户")
async def _(user_id: int, user_in: UserUpdate, request: Request):
    if not user_in.by_user_role_code_list:
        return Fail(code=Code.DUPLICATE_RESOURCE, msg="The user must have at least one role that exists.")

    async with in_transaction("conn_system"):
        user = await user_controller.update(user_id=user_id, obj_in=user_in)
        await user_controller.update_roles_by_code(user, user_in.by_user_role_code_list)

    if user_in.password:
        await _incr_token_version(request, user_id)

    updated_fields = [k for k in user_in.model_dump(exclude_unset=True) if k != "password"]
    radar_log("编辑用户", data={"targetUserId": user_id, "updatedFields": updated_fields, "passwordChanged": bool(user_in.password), "roles": user_in.by_user_role_code_list})
    return Success(msg="Updated Successfully", data={"updated_id": user_id})


# ---- 自定义批量删除（使用 CRUDBase.batch_remove） ----


@router.delete("/users/{user_id}", summary="删除用户")
async def _(user_id: int):
    await user_controller.remove(id=user_id)
    radar_log("删除用户", data={"targetUserId": user_id})
    return Success(msg="Deleted Successfully", data={"deleted_id": user_id})


@router.delete("/users", summary="批量删除用户")
async def _(obj_in: CommonIds):
    deleted_count = await user_controller.batch_remove(obj_in.ids)
    radar_log("批量删除用户", data={"targetUserIds": obj_in.ids, "deletedCount": deleted_count})
    return Success(msg="Deleted Successfully", data={"deleted_count": deleted_count, "deleted_ids": obj_in.ids})


# ---- 自定义扩展接口：用户下线 ----


async def _incr_token_version(request: Request, user_id: int) -> None:
    """递增用户 token_version（DB + Redis 双写）"""
    user = await User.get(id=user_id)
    user.token_version += 1
    await user.save(update_fields=["token_version"])
    redis = request.app.state.redis
    await redis.set(f"token_version:{user_id}", user.token_version)


@router.post("/users/batch-offline", summary="批量用户下线")
async def batch_offline(obj_in: CommonIds, request: Request):
    """按用户ID批量下线"""
    for user_id in obj_in.ids:
        await _incr_token_version(request, int(user_id))
    radar_log("批量用户下线", data={"targetUserIds": obj_in.ids})
    return Success(msg="操作成功")


@router.post("/users/offline-by-role", summary="按角色下线用户")
async def offline_by_role(role_codes: list[str], request: Request):
    """按角色编码批量下线所有关联用户"""
    users = await User.filter(by_user_roles__role_code__in=role_codes).distinct()
    for user in users:
        await _incr_token_version(request, user.id)
    radar_log("按角色下线用户", data={"roleCodes": role_codes, "offlineCount": len(users), "targetUserIds": [u.id for u in users]})
    return Success(msg="操作成功", data={"offlineCount": len(users)})


@router.post("/users/{user_id}/offline", summary="用户下线")
async def user_offline(user_id: int, request: Request):
    """强制单个用户下线"""
    await _incr_token_version(request, user_id)
    radar_log("用户下线", data={"targetUserId": user_id})
    return Success(msg="操作成功")
