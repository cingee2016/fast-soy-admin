from tortoise.expressions import Q

from app.api.v1.utils import generate_tags_recursive_list, refresh_api_list
from app.controllers import user_controller
from app.controllers.api import api_controller
from app.core.ctx import CTX_USER_ID
from app.core.router import CRUDRouter, SearchFieldConfig
from app.models.system import Api, Role
from app.schemas.admin import ApiCreate, ApiSearch, ApiUpdate
from app.schemas.base import Success, SuccessExtra

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
    exclude_fields=["create_time", "update_time"],
    enable_routes={"get", "delete", "batch_delete"},
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

    user_id = CTX_USER_ID.get()
    user_obj = await user_controller.get(id=user_id)
    await user_obj.fetch_related("by_user_roles")
    user_role_objs: list[Role] = await user_obj.by_user_roles
    user_role_codes = [role_obj.role_code for role_obj in user_role_objs]
    if "R_SUPER" in user_role_codes:
        total, api_objs = await api_controller.list(page=obj_in.current, page_size=obj_in.size, search=q, order=["tags", "id"])
    else:
        api_objs: list[Api] = []
        for role_obj in user_role_objs:
            await role_obj.fetch_related("by_role_apis")
            api_objs.extend([api_obj for api_obj in await role_obj.by_role_apis.filter(q)])

        unique_apis = list(set(api_objs))
        sorted_menus = sorted(unique_apis, key=lambda x: x.id)
        start = ((obj_in.current or 1) - 1) * (obj_in.size or 10)
        end = start + (obj_in.size or 10)
        api_objs = sorted_menus[start:end]
        total = len(sorted_menus)

    records = []
    for obj in api_objs:
        data = await obj.to_dict(exclude_fields=["create_time", "update_time"])
        records.append(data)
    data = {"records": records}
    return SuccessExtra(data=data, total=total, current=obj_in.current, size=obj_in.size)


# ---- 覆盖 create/update（需要 tags 特殊处理） ----


@router.post("/apis", summary="创建API")
async def _(api_in: ApiCreate):
    if isinstance(api_in.tags, str):
        api_in.tags = api_in.tags.split("|")
    new_api = await api_controller.create(obj_in=api_in)
    return Success(msg="Created Successfully", data={"created_id": new_api.id})


@router.patch("/apis/{api_id}", summary="更新API")
async def _(api_id: int, api_in: ApiUpdate):
    if isinstance(api_in.tags, str):
        api_in.tags = api_in.tags.split("|")
    await api_controller.update(id=api_id, obj_in=api_in)
    return Success(msg="Update Successfully", data={"updated_id": api_id})


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
    return Success()


@router.post("/apis/tags/all/", summary="查看API tags")
async def _():
    data = await generate_tags_recursive_list()
    return Success(data=data)
