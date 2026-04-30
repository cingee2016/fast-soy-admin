# CRUDBase

`CRUDBase` 是单模型 CRUD 的通用基类，所有 controller 通过继承（或直接实例化）使用。**只负责单张表的增删改查**——跨模型编排、事务、缓存更新、事件派发、外部 IO 统一放在 `services/`。

源码：[app/core/crud.py](../../../app/core/crud.py)。

```python
from app.utils import CRUDBase
from app.business.hr.models import Department


class DepartmentController(CRUDBase[Department, DepartmentCreate, DepartmentUpdate]):
    pass


department_controller = DepartmentController(model=Department)
```

> 多数情况下不需要写 controller 子类——直接 `xxx_controller = CRUDBase(model=Xxx)` 即可。需要重写 `build_search` 等方法时再继承。

## 完整方法列表

### 查询

```python
async def get(self, *args: Q, **kwargs) -> ModelType
async def get_or_none(self, *args: Q, **kwargs) -> ModelType | None
async def exists(self, *args: Q, **kwargs) -> bool
async def count(self, search: Q = Q()) -> int
async def list(
    self,
    page: int | None,
    page_size: int | None,
    search: Q = Q(),
    order: list[str] | None = None,
    fields: list[str] | None = None,
    last_id: int | None = None,
    count_by_pk_field: bool = False,
    select_related: list[str] | None = None,
    prefetch_related: list[str] | None = None,
) -> tuple[Total, list[ModelType]]
```

| 参数 | 用途 |
|---|---|
| `search` | Tortoise `Q` 对象，由 `build_search` 自动构建 |
| `order` | 排序字段列表，前缀 `-` 为降序，例如 `["-created_at", "id"]` |
| `fields` | `only(*fields)` 限制字段（性能优化） |
| `last_id` | 游标分页：`id > last_id`，避免 `OFFSET` 在大表上变慢 |
| `count_by_pk_field` | 启用 `Count(pk, distinct=True)`，处理 join 后 `count()` 重复行的问题 |
| `select_related` | INNER JOIN 预加载（避免 N+1） |
| `prefetch_related` | 子查询预加载（M2M / 反向 FK） |

### 写入

```python
async def create(self, obj_in, exclude=None) -> ModelType
async def batch_create(self, obj_in_list, exclude=None) -> list[ModelType]

async def update(self, id: int, obj_in, exclude=None) -> ModelType
async def batch_update(self, ids: list[int], obj_in, exclude=None) -> int
async def update_by_filter(self, search: Q, obj_in, exclude=None) -> int

async def remove(self, id: int) -> None
async def batch_remove(self, ids: list[int]) -> int
async def remove_by_filter(self, search: Q) -> int
```

特性：

- `obj_in` 接受 Pydantic schema 或 `dict`；schema 走 `model_dump(exclude_unset=True, exclude_none=True)`
- 模型若含 `created_by` / `updated_by` 字段（即继承 `AuditMixin`），自动从 `CTX_USER_ID` 写入
- `update()` 自带事务 `in_transaction(get_db_conn(model))`

### 软删除（需 `SoftDeleteMixin`）

```python
async def soft_remove(self, id: int) -> None
async def soft_batch_remove(self, ids: list[int]) -> int
```

实现是 `UPDATE deleted_at = now()`，模型层 `SoftDeleteManager` 让默认 `Model.filter()` 自动排除软删行，访问已删除行用 `Model.all_objects.filter(...)`。详见 [模型 Mixin / 软删除](./mixins.md#softdeletemixin)。

### 树形（需 `TreeMixin` 或自带 `parent_id`）

```python
async def get_tree(self, search: Q = Q(), order: list[str] | None = None) -> list[ModelType]
async def get_children(self, parent_id: int, search: Q = Q()) -> list[ModelType]
```

`get_tree` 返回**扁平列表**，调用方负责组装嵌套结构（`CRUDRouter(tree_endpoint=True)` 会自动调 `_build_nested_tree` 完成）。

### `build_search` — 从 Schema 自动构建 Q

```python
def build_search(
    self,
    obj_in: BaseModel,
    contains_fields: list[str] | None = None,
    icontains_fields: list[str] | None = None,
    exact_fields: list[str] | None = None,
    iexact_fields: list[str] | None = None,
    in_fields: list[str] | None = None,
    range_fields: list[str] | None = None,
    initial: Q | None = None,
    include_fields: set[str] | None = None,
    exclude_fields: set[str] | None = None,
    extra: Q | None = None,
) -> Q
```

| 字段类别 | Tortoise 操作符 | 备注 |
|---|---|---|
| `contains_fields` | `__contains` | 大小写敏感模糊匹配 |
| `icontains_fields` | `__icontains` | 不区分大小写 |
| `exact_fields` | 直接相等 | — |
| `iexact_fields` | `__iexact` | 不区分大小写 |
| `in_fields` | `__in` | schema 字段值是 list |
| `range_fields` | `__gte` + `__lte` | 对 `created_at`，schema 需提供 `created_at_start` / `created_at_end`（均为可选） |

值为 `None` 或 `""` 的字段会自动跳过。

```python
class DepartmentSearch(PageQueryBase):
    name: str | None = None
    status: str | None = None
    created_at_start: datetime | None = None
    created_at_end: datetime | None = None


q = department_controller.build_search(
    obj_in=search_in,
    contains_fields=["name"],
    exact_fields=["status"],
    range_fields=["created_at"],
)
```

> `CRUDRouter` 内部直接帮你调用 `build_search`，业务里自己用 `build_search` 的场景一般是：在 `@override("list")` 里自定义查询时复用同一套字段配置。

## `get_db_conn(model)` — 选对连接做事务

```python
from tortoise.transactions import in_transaction
from app.utils import get_db_conn

async with in_transaction(get_db_conn(Invoice)):
    await Invoice.create(...)
```

业务模块如果声明了独立 `DB_URL`，模型会落到独立连接 `conn_<biz>`；硬编码连接名会在切库时悄悄出错。详见 [切换数据库 / 业务模块独立数据库](../ops/database.md#业务模块独立数据库进阶)。

## 何时不用 `CRUDBase`

- 跨多模型的写入 → `services/`，而不是写一个怪异的 `controller.create_with_xxx()`
- 复杂报表 / 聚合查询 → 直接在 service 里写 `Model.annotate(...).group_by(...)`
- 需要事务 + 失败补偿 → service + `in_transaction`

## 相关

- [CRUDRouter](./crud-router.md) — 把 6 条标准 REST 路由批量自动生成
- [Schema 基类](./schema.md) — `SchemaBase` / `PageQueryBase` / `make_optional`
- [模型 Mixin](./mixins.md) — `AuditMixin` / `SoftDeleteMixin` / `TreeMixin`
