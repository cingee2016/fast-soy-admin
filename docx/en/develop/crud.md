# CRUDBase

Generic base for single-resource CRUD; every controller inherits from it (or instantiates it directly). **Never produces cross-model side effects** — multi-model orchestration, transactions, and cache writes belong in `services/`.

Source: [`app/core/crud.py`](../../../app/core/crud.py).

```python
from app.utils import CRUDBase
from app.business.hr.models import Department


class DepartmentController(CRUDBase[Department, DepartmentCreate, DepartmentUpdate]):
    pass


department_controller = DepartmentController(model=Department)
```

> Subclassing is rarely needed — `xxx_controller = CRUDBase(model=Xxx)` is enough. Subclass only to override `build_search` or similar.

## Method reference

### Read

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

| Param | Use |
|---|---|
| `search` | Tortoise `Q`; assemble with `build_search` |
| `order` | sort fields, `-` prefix = desc, e.g. `["-created_at", "id"]` |
| `fields` | `only(*fields)` to limit columns (perf) |
| `last_id` | Cursor pagination: `id > last_id`, avoids slow `OFFSET` on large tables |
| `count_by_pk_field` | `Count(pk, distinct=True)` to handle joined-row duplication in `count()` |
| `select_related` | INNER JOIN preload (avoid N+1) |
| `prefetch_related` | sub-query preload (M2M / reverse FK) |

### Write

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

Behavior:

- `obj_in` accepts a Pydantic schema or a `dict`; schemas go through `model_dump(exclude_unset=True, exclude_none=True)`
- If the model has `created_by` / `updated_by` (i.e. inherits `AuditMixin`), they're auto-filled from `CTX_USER_ID`
- `update()` is wrapped in `in_transaction(get_db_conn(model))`

### Soft delete (requires `SoftDeleteMixin`)

```python
async def soft_remove(self, id: int) -> None
async def soft_batch_remove(self, ids: list[int]) -> int
```

Implementation is `UPDATE deleted_at = now()`. The custom manager makes default `Model.filter()` exclude soft-deleted rows; access deleted rows via `Model.all_objects.filter(...)`. See [Mixins / soft delete](/en/develop/mixins#softdeletemixin).

### Tree (requires `TreeMixin` or a custom `parent_id`)

```python
async def get_tree(self, search: Q = Q(), order: list[str] | None = None) -> list[ModelType]
async def get_children(self, parent_id: int, search: Q = Q()) -> list[ModelType]
```

`get_tree` returns a **flat list** — assembling the nested tree is the caller's job (`CRUDRouter(tree_endpoint=True)` does it via `_build_nested_tree`).

### `build_search` — auto-build Q from a schema

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

| Field category | Tortoise op | Notes |
|---|---|---|
| `contains_fields` | `__contains` | case-sensitive substring |
| `icontains_fields` | `__icontains` | case-insensitive substring |
| `exact_fields` | direct equal | — |
| `iexact_fields` | `__iexact` | case-insensitive |
| `in_fields` | `__in` | schema field is a list |
| `range_fields` | `__gte` + `__lte` | for `created_at`, the schema needs `created_at_start` / `created_at_end` (both optional) |

Empty (`None` / `""`) values are skipped.

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

> `CRUDRouter` calls `build_search` for you. You'd call it directly when reusing the same field config in `@override("list")`.

## `get_db_conn(model)` — pick the right connection for a transaction

```python
from tortoise.transactions import in_transaction
from app.utils import get_db_conn

async with in_transaction(get_db_conn(Invoice)):
    await Invoice.create(...)
```

If a business module declares its own `DB_URL`, its models live on `conn_<biz>`; hard-coded connection names quietly break when switching DBs. See [Database / standalone DB](/en/ops/database#business-module-standalone-database-advanced).

## When *not* to use `CRUDBase`

- Multi-model writes → `services/`, not a weird `controller.create_with_xxx()`
- Complex aggregation / reports → write `Model.annotate(...).group_by(...)` directly in a service
- Transactional + compensating writes → service + `in_transaction`

## See also

- [CRUDRouter](/en/develop/crud-router) — generates the standard 6 REST routes
- [Schema base](/en/develop/schema) — `SchemaBase` / `PageQueryBase` / `make_optional`
- [Model mixins](/en/develop/mixins) — `AuditMixin` / `SoftDeleteMixin` / `TreeMixin`
