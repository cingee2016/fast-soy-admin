from collections.abc import Callable
from dataclasses import dataclass, field

from fastapi import APIRouter, Query
from pydantic import BaseModel
from tortoise.expressions import Q

from app.core.base_schema import CommonIds, Success, SuccessExtra
from app.core.crud import CRUDBase


@dataclass
class SearchFieldConfig:
    """搜索字段配置，用于自动构建 Q 查询"""

    contains_fields: list[str] = field(default_factory=list)
    icontains_fields: list[str] = field(default_factory=list)
    exact_fields: list[str] = field(default_factory=list)
    iexact_fields: list[str] = field(default_factory=list)
    in_fields: list[str] = field(default_factory=list)


class CRUDRouter:
    """
    CRUD Router 工厂，自动生成标准 CRUD 接口，同时支持自定义扩展。

    用法:
        # 基础用法 — 一行生成标准 CRUD
        crud_router = CRUDRouter(
            prefix="/roles",
            controller=role_controller,
            create_schema=RoleCreate,
            update_schema=RoleUpdate,
            search_fields=SearchFieldConfig(
                contains_fields=["role_name", "role_code"],
                exact_fields=["status_type"],
            ),
            summary_prefix="角色",
        )

        # 扩展自定义接口
        @crud_router.router.get("/roles/{role_id}/menus", summary="查看角色菜单")
        async def get_role_menus(role_id: int):
            ...

        # 在 __init__.py 中注册
        router_system_manage.include_router(crud_router.router)
    """

    def __init__(
        self,
        prefix: str,
        controller: CRUDBase,
        create_schema: type[BaseModel] | None = None,
        update_schema: type[BaseModel] | None = None,
        list_schema: type[BaseModel] | None = None,
        search_fields: SearchFieldConfig | None = None,
        summary_prefix: str = "",
        list_order: list[str] | None = None,
        exclude_fields: list[str] | None = None,
        enable_routes: set[str] | None = None,
        list_method: str = "get",
        batch_delete_method: str = "query",
        record_transform: Callable | None = None,
    ):
        """
        Args:
            prefix: 路由前缀，如 "/roles"
            controller: CRUDBase 控制器实例
            create_schema: 创建 schema
            update_schema: 更新 schema
            list_schema: 列表搜索 schema（POST 列表时使用）
            search_fields: 搜索字段配置
            summary_prefix: 接口 summary 前缀，如 "角色"
            list_order: 列表排序字段，默认 ["id"]
            exclude_fields: to_dict 时排除的字段
            enable_routes: 启用的路由集合，默认全部启用。可选值: list, get, create, update, delete, batch_delete
            list_method: 列表接口方法 "get"(Query参数) 或 "post"(Body搜索)
            batch_delete_method: 批量删除参数方式 "query"(逗号分隔) 或 "body"(CommonIds)
            record_transform: 自定义记录转换函数，签名: async def transform(obj) -> dict
        """
        self.prefix = prefix
        self.controller = controller
        self.create_schema = create_schema
        self.update_schema = update_schema
        self.list_schema = list_schema
        self.search_fields = search_fields or SearchFieldConfig()
        self.summary_prefix = summary_prefix
        self.list_order = list_order or ["id"]
        self.exclude_fields = exclude_fields or []
        self.list_method = list_method
        self.batch_delete_method = batch_delete_method
        self.record_transform = record_transform

        # 资源名（从 prefix 提取，如 "/roles" -> "roles"）
        self._resource = prefix.strip("/").split("/")[-1]

        all_routes = {"list", "get", "create", "update", "delete", "batch_delete"}
        self.enable_routes = enable_routes if enable_routes is not None else all_routes

        self.router = APIRouter()
        self._register_routes()

    def _register_routes(self):
        if "list" in self.enable_routes:
            self._add_list_route()
        if "get" in self.enable_routes:
            self._add_get_route()
        if "create" in self.enable_routes:
            self._add_create_route()
        if "update" in self.enable_routes:
            self._add_update_route()
        if "delete" in self.enable_routes:
            self._add_delete_route()
        if "batch_delete" in self.enable_routes:
            self._add_batch_delete_route()

    async def _to_record(self, obj) -> dict:
        if self.record_transform:
            return await self.record_transform(obj)
        return await obj.to_dict(exclude_fields=self.exclude_fields)

    # ---- 路由注册方法 ----

    def _add_list_route(self):
        controller = self.controller
        search_fields = self.search_fields
        list_order = self.list_order
        to_record = self._to_record

        if self.list_method == "post" and self.list_schema:
            schema = self.list_schema

            @self.router.post(f"/{self._resource}/all/", summary=f"查看{self.summary_prefix}列表")
            async def list_items(obj_in: schema):  # type: ignore[valid-type]
                q = controller.build_search(
                    obj_in,
                    contains_fields=search_fields.contains_fields,
                    icontains_fields=search_fields.icontains_fields,
                    exact_fields=search_fields.exact_fields,
                    iexact_fields=search_fields.iexact_fields,
                    in_fields=search_fields.in_fields,
                )
                total, objs = await controller.list(page=obj_in.current, page_size=obj_in.size, search=q, order=list_order)
                records = [await to_record(obj) for obj in objs]
                data = {"records": records}
                return SuccessExtra(data=data, total=total, current=obj_in.current, size=obj_in.size)

        else:

            @self.router.get(f"/{self._resource}", summary=f"查看{self.summary_prefix}列表")
            async def list_items_get(
                current: int = Query(1, description="页码"),
                size: int = Query(10, description="每页数量"),
            ):
                total, objs = await controller.list(page=current, page_size=size, search=Q(), order=list_order)
                records = [await to_record(obj) for obj in objs]
                data = {"records": records}
                return SuccessExtra(data=data, total=total, current=current, size=size)

    def _add_get_route(self):
        controller = self.controller
        to_record = self._to_record

        @self.router.get(f"/{self._resource}/{{item_id}}", summary=f"查看{self.summary_prefix}")
        async def get_item(item_id: int):
            obj = await controller.get(id=item_id)
            return Success(data=await to_record(obj))

    def _add_create_route(self):
        if not self.create_schema:
            return

        controller = self.controller
        schema = self.create_schema

        @self.router.post(f"/{self._resource}", summary=f"创建{self.summary_prefix}")
        async def create_item(obj_in: schema):  # type: ignore[valid-type]
            new_obj = await controller.create(obj_in=obj_in)
            return Success(msg="Created Successfully", data={"created_id": new_obj.id})

    def _add_update_route(self):
        if not self.update_schema:
            return

        controller = self.controller
        schema = self.update_schema

        @self.router.patch(f"/{self._resource}/{{item_id}}", summary=f"更新{self.summary_prefix}")
        async def update_item(item_id: int, obj_in: schema):  # type: ignore[valid-type]
            await controller.update(id=item_id, obj_in=obj_in)
            return Success(msg="Updated Successfully", data={"updated_id": item_id})

    def _add_delete_route(self):
        controller = self.controller

        @self.router.delete(f"/{self._resource}/{{item_id}}", summary=f"删除{self.summary_prefix}")
        async def delete_item(item_id: int):
            await controller.remove(id=item_id)
            return Success(msg="Deleted Successfully", data={"deleted_id": item_id})

    def _add_batch_delete_route(self):
        controller = self.controller

        if self.batch_delete_method == "body":

            @self.router.delete(f"/{self._resource}", summary=f"批量删除{self.summary_prefix}")
            async def batch_delete_by_body(obj_in: CommonIds):
                deleted_count = await controller.batch_remove(obj_in.ids)
                return Success(msg="Deleted Successfully", data={"deleted_count": deleted_count, "deleted_ids": obj_in.ids})

        else:

            @self.router.delete(f"/{self._resource}", summary=f"批量删除{self.summary_prefix}")
            async def batch_delete_by_query(ids: str = Query(..., description="ID列表, 用逗号隔开")):
                id_list = [int(i) for i in ids.split(",")]
                deleted_count = await controller.batch_remove(id_list)
                return Success(msg="Deleted Successfully", data={"deleted_count": deleted_count, "deleted_ids": id_list})
