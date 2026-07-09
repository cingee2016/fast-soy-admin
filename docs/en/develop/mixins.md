# Model Mixins

All Tortoise models should inherit `BaseModel` and mix in the mixins they need. Source: `app/core/base_model.py` and `app/core/soft_delete.py`.

```python
# pyright: reportIncompatibleVariableOverride=false
from tortoise import fields

from app.utils import AuditMixin, BaseModel, SoftDeleteMixin, StatusType, TreeMixin


class Warehouse(BaseModel, AuditMixin, TreeMixin, SoftDeleteMixin):
    """Warehouse"""

    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=100, unique=True, description="warehouse name")
    code = fields.CharField(max_length=50, unique=True, description="warehouse code")
    status = fields.CharEnumField(enum_type=StatusType, default=StatusType.enable, description="status")

    class Meta:
        table = "biz_inventory_warehouse"
        table_description = "Warehouse"
```

> `# pyright: reportIncompatibleVariableOverride=false` is a known false-positive suppression for Tortoise + Pyright; add it to every model file.

## BaseModel

`BaseModel(models.Model)` provides `to_dict()` — converts an instance to a **camelCase** dict, handling:

- `datetime` → millisecond timestamp; also outputs a formatted string field `fmtCreatedAt` etc. (toggleable)
- `Decimal` → `float`
- `Enum` → `value`
- `UUID` → `str`
- PK + FK (`id` / `*_id`) → **sqid string**; `0` (root / empty-reference semantics) is preserved as `0`

```python
async def to_dict(
    self,
    include_fields: list[str] | None = None,   # whitelist
    exclude_fields: list[str] | None = None,   # blacklist
    m2m: bool = False,                         # serialize M2M relations
    fmt_datetime: bool = True,                 # output formatted datetime fields
)
```

```python
data = await user.to_dict(exclude_fields=["password", "created_by", "updated_by"])
return Success(data=data)
```

> `CRUDRouter` calls `obj.to_dict(exclude_fields=...)` for you.

## AuditMixin

```python
created_by = CharField(max_length=64, null=True)
created_at = DatetimeField(auto_now_add=True)
updated_by = CharField(max_length=64, null=True)
updated_at = DatetimeField(auto_now=True)
```

`CRUDBase.create / update / soft_remove` auto-write `created_by` / `updated_by` from `CTX_USER_ID` (stringified user id).

::: tip Use it on every persisted model
Even immutable seed data benefits massively for incident debugging.
:::

## TreeMixin

```python
parent_id = IntField(default=0)   # 0 = top
order     = IntField(default=0)
level     = IntField(default=1)   # redundant; maintained by business code
```

Conventions:

- `parent_id = 0` is the root
- `level` is **not** auto-maintained — set it on write as `parent.level + 1` (if you use it)
- For tree serialization use `CRUDRouter(tree_endpoint=True)` — calls `_build_nested_tree(records, parent_id_key="parentId", root_value=0)`

::: warning Don't add TreeMixin to Menu
`Menu` already declares its own `parent_id` / `order` — mixing in conflicts.
:::

## SoftDeleteMixin

Source: `app/core/soft_delete.py`.

```python
deleted_at = DatetimeField(null=True, default=None)
```

Behavior:

- Default Manager is replaced by `SoftDeleteManager`; `Model.filter()` / `.all()` / `.get()` auto-add `deleted_at IS NULL`
- Soft delete via `controller.soft_remove(id=...)` — `UPDATE deleted_at = now()` + refresh `updated_by`
- Access deleted rows via `Model.all_objects.filter(deleted_at__isnull=False)`

```python
# soft delete
await dept_controller.soft_remove(id=1)

# default query excludes deleted
await Warehouse.filter(name="Engineering")          # deleted_at IS NULL

# include deleted
await Warehouse.all_objects.all()
```

### PostgreSQL: partial unique index

`SoftDeleteMixin` paired with `unique=True` is tricky — soft-deleted rows still hold the constraint. In production on PostgreSQL replace plain `UNIQUE` with a partial index:

```sql
CREATE UNIQUE INDEX biz_warehouse_code_active_uq
    ON biz_warehouse(code)
    WHERE deleted_at IS NULL;
```

SQLite doesn't support `WHERE` partial indexes — enforce in app layer (`controller.exists`).

## Working with CRUDRouter

```python
CRUDRouter(
    ...,
    soft_delete=True,        # delete / batch_delete use soft_remove
    tree_endpoint=True,      # register GET /resources/tree
)
```

## Custom mixins

Need a recurring field in your business (e.g. multi-tenant `tenant_id`)? Define your own:

```python
class TenantMixin:
    tenant_id = fields.IntField(db_index=True, description="tenant id")

    class Meta:
        abstract = True
```

`abstract = True` is required, otherwise Tortoise tries to create a separate table for the mixin.

## See also

- [Data models (system)](/en/develop/models) — full field listings
- [CRUDBase](/en/develop/crud) — `soft_remove` / `get_tree` etc.
- [Sqids](/en/develop/sqids) — how PK / FK become sqid strings
