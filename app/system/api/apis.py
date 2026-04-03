from tortoise.expressions import Q

from app.core.base_schema import CommonIds, Success, SuccessExtra
from app.core.ctx import CTX_ROLE_CODES
from app.core.router import CRUDRouter, SearchFieldConfig
from app.system.api.utils import generate_tags_recursive_list, refresh_api_list
from app.system.controllers import api_controller
from app.system.models import Api, Role
from app.system.radar.developer import radar_log
from app.system.schemas.admin import ApiCreate, ApiSearch, ApiUpdate

# 标准 CRUD 路由：get, create, update, delete, batch_delete
# list 和 create 需要自定义逻辑，不自动生成
crud = CRUDRouter(
    prefix="/apis",
    controller=api_controller,
    create_schema=ApiCreate,
    update_schema=ApiUpdate,
    search_fields=SearchFieldConfig(
        contains_fields=["api_path"],
        exact_fields=["summary", "status_type"],
    ),
    summary_prefix="API",
    list_order=["tags", "id"],
    exclude_fields=["created_at", "updated_at"],
    enable_routes={"get"},
)
router = crud.router


# ---- 自定义 list（需要权限过滤和 tags 特殊处理） ----


@router.post("/apis/all/", summary="查看API列表")
async def _(obj_in: ApiSearch):
    q = api_controller.build_search(
        obj_in,
        contains_fields=["api_path"],
        exact_fields=["summary", "status_type"],
    )
    if obj_in.tags:
        for tag in obj_in.tags:
            q &= Q(tags__contains=[tag])

    # 排除系统自动注册的 API，只显示用户手动创建的
    q &= Q(is_system=False)

    role_codes = CTX_ROLE_CODES.get()
    if "R_SUPER" in role_codes:
        total, api_objs = await api_controller.list(page=obj_in.current, page_size=obj_in.size, search=q, order=["tags", "id"])
    else:
        # 非超管：只返回角色关联的 API
        role_objs = await Role.filter(role_code__in=role_codes).prefetch_related("by_role_apis")
        all_apis: list[Api] = []
        for role_obj in role_objs:
            all_apis.extend([api_obj for api_obj in await role_obj.by_role_apis.filter(q)])

        unique_apis = sorted(set(all_apis), key=lambda x: x.id)
        start = ((obj_in.current or 1) - 1) * (obj_in.size or 10)
        end = start + (obj_in.size or 10)
        api_objs = unique_apis[start:end]
        total = len(unique_apis)

    records = [await obj.to_dict(exclude_fields=["created_at", "updated_at"]) for obj in api_objs]
    data = {"records": records}
    return SuccessExtra(data=data, total=total, current=obj_in.current, size=obj_in.size)


# ---- 覆盖 create/update（需要 tags 特殊处理） ----


@router.post("/apis", summary="创建API")
async def _(api_in: ApiCreate):
    if isinstance(api_in.tags, str):
        api_in.tags = api_in.tags.split("|")
    new_api = await api_controller.create(obj_in=api_in)
    radar_log("创建API", data={"apiId": new_api.id, "apiPath": api_in.api_path, "summary": api_in.summary})
    return Success(msg="Created Successfully", data={"created_id": new_api.id})


@router.patch("/apis/{api_id}", summary="更新API")
async def _(api_id: int, api_in: ApiUpdate):
    if isinstance(api_in.tags, str):
        api_in.tags = api_in.tags.split("|")
    await api_controller.update(id=api_id, obj_in=api_in)
    radar_log("编辑API", data={"apiId": api_id, "apiPath": api_in.api_path, "summary": api_in.summary})
    return Success(msg="Update Successfully", data={"updated_id": api_id})


# ---- 自定义删除（需要日志追踪） ----


@router.delete("/apis/{api_id}", summary="删除API")
async def _(api_id: int):
    api_obj = await api_controller.get(id=api_id)
    radar_log("删除API", data={"apiId": api_id, "apiPath": api_obj.api_path, "summary": api_obj.summary})
    await api_controller.remove(id=api_id)
    return Success(msg="Deleted Successfully", data={"deleted_id": api_id})


@router.delete("/apis", summary="批量删除API")
async def _(obj_in: CommonIds):
    api_objs = await Api.filter(id__in=obj_in.ids)
    radar_log("批量删除API", data={"apiIds": obj_in.ids, "apiPaths": [a.api_path for a in api_objs]})
    deleted_count = await api_controller.batch_remove(obj_in.ids)
    return Success(msg="Deleted Successfully", data={"deleted_count": deleted_count, "deleted_ids": obj_in.ids})


# ---- 自定义扩展接口 ----


def build_api_tree(apis: list[Api]):
    parent_map = {"root": {"id": "root", "children": []}}
    for api in apis:
        tags = api.tags
        parent_id = "root"
        for tag in tags:
            node_id = f"parent${tag}"
            if node_id not in parent_map:
                node = {"id": node_id, "summary": tag, "children": []}
                parent_map[node_id] = node
                parent_map[parent_id]["children"].append(node)
            parent_id = node_id
        parent_map[parent_id]["children"].append({
            "id": api.id,
            "summary": api.summary,
        })
    return parent_map["root"]["children"]


@router.get("/apis/tree/", summary="查看API树")
async def _():
    api_objs = await Api.all()
    data = []
    if api_objs:
        data = build_api_tree(api_objs)
    return Success(data=data)


@router.post("/apis/refresh/", summary="刷新API列表")
async def _():
    await refresh_api_list()
    radar_log("刷新API列表")
    return Success()


@router.post("/apis/tags/all/", summary="查看API tags")
async def _():
    data = await generate_tags_recursive_list()
    return Success(data=data)
