# CRUDRouter

`CRUDRouter` 批量生成 6 条标准 REST 路由，配合 [`CRUDBase`](./crud.md) 和 [API 约定](./api.md) 使用，消灭 90% 的样板代码。

源码：[app/core/router.py](../../../app/core/router.py)。

## 生成的 6 条标准路由

| 名称 | 方法 + 路径 | 启用条件 | Body / Param |
|---|---|---|---|
| `list` | `POST /{prefix}/search` | 传 `list_schema` | `list_schema`（含 `current/size/orderBy`） |
| `get` | `GET /{prefix}/{item_id}` | 始终 | `item_id: SqidPath` |
| `create` | `POST /{prefix}` | 传 `create_schema` | `create_schema` |
| `update` | `PATCH /{prefix}/{item_id}` | 传 `update_schema` | `item_id` + `update_schema` |
| `delete` | `DELETE /{prefix}/{item_id}` | 始终 | `item_id` |
| `batch_delete` | `DELETE /{prefix}` | 始终 | `CommonIds`（`{ids: [...]}`） |

`tree_endpoint=True` 时额外注册 `GET /{prefix}/tree`。

## 最简用法

```python
from app.utils import CRUDBase, CRUDRouter, SearchFieldConfig

tag_controller = CRUDBase(model=Tag)

tag_crud = CRUDRouter(
    prefix="/tags",
    controller=tag_controller,
    create_schema=TagCreate,
    update_schema=TagUpdate,
    list_schema=TagSearch,
    search_fields=SearchFieldConfig(
        contains_fields=["name"],
        exact_fields=["category"],
    ),
    summary_prefix="标签",
)
router = tag_crud.router
```

`prefix` 必须以斜杠开头（`/tags`），资源名（最后一段）会被用作生成的路径片段。

## 完整参数

```python
CRUDRouter(
    prefix: str,
    controller: CRUDBase,
    create_schema: type[BaseModel] | None = None,
    update_schema: type[BaseModel] | None = None,
    list_schema: type[BaseModel] | None = None,
    search_fields: SearchFieldConfig | None = None,
    summary_prefix: str = "",
    list_order: list[str] | None = None,           # 默认 ["id"]
    exclude_fields: list[str] | None = None,       # to_dict 排除
    enable_routes: set[str] | None = None,         # 默认全部
    record_transform: Callable | None = None,      # async def transform(obj) -> dict
    soft_delete: bool = False,                     # 走 controller.soft_remove
    tree_endpoint: bool = False,                   # 注册 GET /tree
    action_dependencies: dict[str, Sequence] | None = None,
)
```

### `search_fields: SearchFieldConfig`

```python
SearchFieldConfig(
    contains_fields=[...],     # __contains
    icontains_fields=[...],    # __icontains
    exact_fields=[...],        # 直接相等
    iexact_fields=[...],       # __iexact
    in_fields=[...],           # __in
    range_fields=[...],        # 期望 schema 含 {field}_start / {field}_end
)
```

详见 [`build_search`](./crud.md#build_search--从-schema-自动构建-q)。

### `enable_routes` — 关闭某些路由

```python
crud = CRUDRouter(..., enable_routes={"list", "get"})  # 只读
```

### `record_transform` — 自定义返回 dict

默认列表 / 详情都用 `await obj.to_dict(exclude_fields=...)`。需要做关联预加载或拼字段时：

```python
async def transform(obj: Employee) -> dict:
    d = await obj.to_dict()
    await obj.fetch_related("department")
    d["departmentName"] = obj.department.name
    return d

CRUDRouter(..., record_transform=transform)
```

> 仅推荐少量字段补齐场景。需要 N+1 优化（`select_related` / `prefetch_related`）时直接 `@override("list")` 更直接。

### `soft_delete` — 软删除

需要模型继承 `SoftDeleteMixin`。

```python
CRUDRouter(..., soft_delete=True)
# delete       → controller.soft_remove
# batch_delete → controller.soft_batch_remove
```

### `tree_endpoint` — 树形端点

需要模型有 `parent_id` 字段（建议继承 `TreeMixin`）。生成的 `GET /resources/tree` 用 `_build_nested_tree(records, parent_id_key="parentId", root_value=0)` 把扁平列表组装成嵌套结构。

### `action_dependencies` — 按路由挂依赖

```python
CRUDRouter(
    ...,
    action_dependencies={
        "create":       [require_buttons("B_HR_DEPT_CREATE")],
        "update":       [require_buttons("B_HR_DEPT_EDIT")],
        "delete":       [require_buttons("B_HR_DEPT_DELETE")],
        "batch_delete": [require_buttons("B_HR_DEPT_DELETE")],
    },
)
```

**关键特性**：`action_dependencies` 对 `@override("create")` 替换的路由**同样生效**——所以业务上不会出现"自定义实现忘了挂权限"的事故。

## 自定义某条路由：`@crud.override`

需要自定义逻辑时**不要**重新写一个 `@router.post("/users")` 覆盖——会被 `_OrderedRouter` 排序后命中默认路由。请用：

```python
@user_crud.override("create")
async def _create_user(user_in: UserCreate, request: Request):
    ...   # 自定义逻辑
    return Success(...)
```

`override` 做了三件事：

1. 从 router 中移除默认实现（按 path + methods 精确匹配）
2. 用你的函数注册到同一 path / methods / summary
3. 自动挂上 `action_dependencies[name]` 的依赖

各路由的标准签名（也可以 `crud.get_route_info("create")` 查）：

```text
list:         async def list_items(obj_in: <list_schema>)
get:          async def get_item(item_id: SqidPath)
create:       async def create_item(obj_in: <create_schema>)
update:       async def update_item(item_id: SqidPath, obj_in: <update_schema>)
delete:       async def delete_item(item_id: SqidPath)
batch_delete: async def batch_delete(obj_in: CommonIds)
```

参数可以**任意扩展**（FastAPI 依赖语义），如：

```python
@user_crud.override("update")
async def _update(item_id: SqidPath, obj_in: UserUpdate, request: Request):
    redis = request.app.state.redis
    ...
```

::: warning 不传 schema 不会生成对应路由
`emp_crud` 没传 `create_schema` 时，CRUDRouter 不会注册 `POST /employees`。这正好让你能在同一 router 上手写 `@router.post("/employees")` 而不被覆盖——HR 模块的员工创建就是这样。
:::

## 适用边界 — 别让 CRUDRouter 上瘾

`CRUDRouter` 是给**贫血资源**用的——字典、标签、部门、分类这种纯 CRUD 表。聚合根（用户、角色、订单、工单等带状态、带副作用的资源）**不要硬塞进 CRUDRouter**。

::: danger 触发改写信号
满足以下任一条件，立刻把该资源改写为显式 `@router.post(...)` + `services/`，不要继续 `@crud.override`：

- override 数 ≥ 3（标准 6 路由覆盖一半，抽象已无收益）
- 任一 override 内出现 `in_transaction` / `redis` / 跨模型写
- 资源是聚合根或带状态机
- 写操作有副作用（发通知、写审计、触发事件、失效缓存）
:::

### `@crud.override` 内禁止出现

下面这些必须下沉到 `services/`，api 层只做"参数转发 + 包响应"：

- `in_transaction(...)` —— 事务编排是 service 的事
- `request.app.state.redis` / 任何 Redis 客户端调用
- 跨模型的 `create` / `update` / `delete`（含 `m2m.add` / `m2m.clear`）
- 调用其他模块的 service / 发事件 / 写审计

### 正确范式

```python
# services/users.py
async def create_user_with_roles(redis, user_in: UserCreate) -> User:
    if await user_controller.get_by_email(user_in.user_email):
        raise BizError(code=Code.DUPLICATE_USER_EMAIL, msg="该邮箱已被注册")
    async with in_transaction(get_db_conn(User)):
        user = await user_controller.create(obj_in=user_in)
        await user_controller.update_roles_by_code(user, user_in.by_user_role_code_list)
    return user

# api/users.py
@crud.override("create")
async def _create_user(user_in: UserCreate, request: Request):
    user = await create_user_with_roles(request.app.state.redis, user_in)
    return Success(msg="创建成功", data={"createdId": encode_id(user.id)})
```

仓库内参考实现：

- [`app/system/api/users.py`](https://github.com/sleep1223/fast-soy-admin/blob/main/app/system/api/users.py) ＋ [`app/system/services/user.py`](https://github.com/sleep1223/fast-soy-admin/blob/main/app/system/services/user.py)
- [`app/system/api/apis.py`](https://github.com/sleep1223/fast-soy-admin/blob/main/app/system/api/apis.py) ＋ [`app/system/services/api.py`](https://github.com/sleep1223/fast-soy-admin/blob/main/app/system/services/api.py)

> 这条约定也作为 PR review checklist 第 15 条强制执行，见 [架构总览 / 强制约定清单](../getting-started/architecture.md)。

## 在 router 上加额外端点

`crud.router` 是普通 `APIRouter`，标准 6 路由之外的端点直接挂：

```python
router = dept_crud.router

@router.post("/departments/{dept_id}/employees", summary="批量分配员工")
async def assign_employees(dept_id: SqidPath, body: AssignEmployees):
    ...
    return Success(...)
```

## 业务模块的接线模板

```python
# app/business/hr/api/manage.py
from fastapi import APIRouter

from app.utils import CRUDRouter, DependPermission, SearchFieldConfig, require_buttons

dept_crud = CRUDRouter(
    prefix="/departments",
    controller=department_controller,
    create_schema=DepartmentCreate,
    update_schema=DepartmentUpdate,
    list_schema=DepartmentSearch,
    search_fields=SearchFieldConfig(contains_fields=["name", "code"]),
    summary_prefix="部门",
    soft_delete=True,
    tree_endpoint=True,
    action_dependencies={
        "create": [require_buttons("B_HR_DEPT_CREATE")],
        "update": [require_buttons("B_HR_DEPT_EDIT")],
        "delete": [require_buttons("B_HR_DEPT_DELETE")],
        "batch_delete": [require_buttons("B_HR_DEPT_DELETE")],
    },
)

# 主路由：可以在此挂模块前缀和默认依赖
router = APIRouter(prefix="/hr", tags=["hr"], dependencies=[DependPermission])
router.include_router(dept_crud.router)

# api/__init__.py 把 manage / dept / my 三个子 router 汇总到顶层 router
```

业务模块的 `api/__init__.py` 必须导出 `router: APIRouter`，autodiscover 才能挂载到 `/api/v1/business/`。

## 路由顺序：静态优先

`CRUDRouter.router` 是 `_OrderedRouter`，每次 `add_api_route` 后自动重排：不含 `{...}` 的路径排在前面。这保证后挂的 `GET /resources/pages` 不会被先挂的 `GET /resources/{item_id}` 遮蔽。

> 如果你在 router 上手动 `router.routes.append(...)` 绕过 `add_api_route`，排序不会触发——别这么干。

## 相关

- [CRUDBase](./crud.md) — `controller.list / build_search / soft_remove ...`
- [API 约定](./api.md) — 路径 / 方法 / 命名 / 响应
- [Schema 基类](./schema.md) — `PageQueryBase` / `make_optional` / `CommonIds`
- [认证与权限](./auth.md) — `require_buttons` / `require_roles`
