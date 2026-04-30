# Development Guide

End-to-end flow for adding a business module. The CLI only asks you to write `models.py`; schemas, controllers, API, frontend views and i18n are generated.

## Prerequisites

Run all commands from the project root. First-time setup:

```bash
make install-all    # backend + frontend deps
make initdb         # first-time DB init (only once)
```

## Walkthrough: `inventory` (warehouse management)

### 1. Create the module skeleton

```bash
make cli-init MOD=inventory
# Will prompt for the Chinese name, e.g. "Inventory"
```

Generates:

```
app/business/inventory/
├── __init__.py
└── models.py          # only common imports + sample comments
```

### 2. Edit `models.py`

```python
# pyright: reportIncompatibleVariableOverride=false
"""Inventory module — business models."""

from tortoise import fields

from app.utils import AuditMixin, BaseModel, StatusType


class Warehouse(BaseModel, AuditMixin):
    """Warehouse"""

    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=100, unique=True, description="warehouse name")
    code = fields.CharField(max_length=50, unique=True, description="warehouse code")
    address = fields.CharField(max_length=255, null=True, description="address")
    status = fields.CharEnumField(enum_type=StatusType, default=StatusType.enable, description="status")

    class Meta:
        table = "biz_inventory_warehouse"
        table_description = "Warehouse"


class Product(BaseModel, AuditMixin):
    """Product"""

    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=100, description="product name")
    sku = fields.CharField(max_length=50, unique=True, description="SKU")
    price = fields.DecimalField(max_digits=10, decimal_places=2, description="price")
    stock = fields.IntField(default=0, description="stock")
    status = fields.CharEnumField(enum_type=StatusType, default=StatusType.enable, description="status")

    warehouse: fields.ForeignKeyRelation["Warehouse"] = fields.ForeignKeyField(
        "models.Warehouse", related_name="products", description="warehouse"
    )

    class Meta:
        table = "biz_inventory_product"
        table_description = "Product"
```

Conventions:

- inherit `BaseModel, AuditMixin`
- every field has `description="..."` (CLI uses it as i18n label, truncated to first sentence)
- class docstring is the resource name
- `Meta.table` uses `biz_<module>_<entity>` prefix

### 3. Generate backend code

```bash
make cli-gen MOD=inventory
```

Interactively select fuzzy-search fields (Enter accepts all). Generates:

```
app/business/inventory/
├── __init__.py
├── models.py
├── schemas.py          # Pydantic Create/Update/Search
├── controllers.py      # CRUDBase instances
├── services.py         # business orchestration placeholder
├── init_data.py        # menu / role / seed placeholder
└── api/
    ├── __init__.py
    └── manage.py       # CRUDRouter generates 6 standard endpoints
```

Auto runs `ruff check --fix` + `ruff format`.

### 4. Generate frontend code

```bash
make cli-gen-web MOD=inventory CN=Inventory
```

> Or `make cli-gen-all MOD=inventory CN=Inventory` to do steps 3 + 4 in one shot.

Pick list-display and search fields per model. Generates:

```
web/
├── src/service/api/inventory-manage.ts        # CRUD calls
├── src/typings/api/inventory-manage.d.ts      # TS types
├── src/views/inventory/<entity>/
│   ├── index.vue                              # list page
│   └── modules/
│       ├── <entity>-search.vue                # search form
│       └── <entity>-operate-drawer.vue        # add / edit drawer
└── src/locales/langs/_generated/inventory/
    ├── zh-cn.ts                               # i18n messages (auto-merged, no manual step)
    ├── en-us.ts                               # i18n messages (auto-merged)
    └── types.d.ts                             # GeneratedPages augmentation (auto via declaration merging)
```

`web/src/service/api/index.ts` auto-appends `export * from './inventory-manage';` (idempotent).

Auto runs `oxfmt` + `eslint --fix`.

### 5. i18n is auto-merged

The three files under `_generated/<module>/` are consumed by the frontend toolchain; no manual edits to the global language packs are required.

| File | Consumer | Effect |
|---|---|---|
| `zh-cn.ts` / `en-us.ts` | [`web/src/locales/locale.ts`](https://github.com/sleep1223/fast-soy-admin/blob/dev/web/src/locales/locale.ts) deep-merges them into the matching messages via `import.meta.glob` | Injects `route.<module>` and `page.<module>` |
| `types.d.ts` | Augments `App.I18n.GeneratedPages` via TypeScript declaration merging | Makes `$t('page.<module>.<entity>.xxx')` checkable by `vue-tsc` |

Type contract:

- `App.I18n.Schema.page` is intersected with `_MergePages<GeneratedPages>`; a new module only needs `interface GeneratedPages { <module>: {...} }` to extend the key space.
- Base packs `zh-cn.ts` / `en-us.ts` are typed as `App.I18n.BaseSchema` (`Schema` minus `GeneratedPages`), so new modules never force edits to the base files.
- `App.I18n.Schema.route` is `Partial<Record<I18nRouteKey, string>>`. Route keys are derived by Elegant Router from `views/`; their translations are supplied by `_generated/<module>/zh-cn.ts`.

### 6. Resolve TODOs

Foreign keys / custom enums in the frontend can't auto-derive their dropdown source. Search for `// TODO` and fill in `options` (typically `fetchGetXxxList`).

### 7. Migrate the database

```bash
make mm         # = makemigrations + migrate
```

### 8. Run + verify

```bash
make dev        # both servers
```

Visit `http://localhost:9527`, log in, navigate to `/inventory/warehouse` and `/inventory/product` to verify CRUD.

### 9. Pre-push gate

```bash
make check-all  # backend + frontend full check
```

## Field-type cheat sheet

CLI maps Tortoise field types to TS / form widgets:

| Tortoise field | TS type | Backend schema | Frontend form | Frontend search |
|---|---|---|---|---|
| `CharField` | `string` | `str` | `NInput` | `NInput` |
| `TextField` | `string` | `str` | `NInput type="textarea"` | `NInput` |
| `IntField` / `BigIntField` | `number` | `int` | `NInputNumber` | `NInputNumber` |
| `DecimalField` / `FloatField` | `number` | `Decimal` / `float` | `NInputNumber :precision="2"` | skipped |
| `BooleanField` | `boolean` | `bool` | `NSwitch` | — |
| `DateField` | `string` | `date` | `NDatePicker type="date"` | — |
| `DatetimeField` | `string` | `datetime` | `NDatePicker type="datetime"` | — |
| `CharEnumField(StatusType)` | `string` | `StatusType` | `NSelect statusTypeOptions` | same |
| `CharEnumField(other)` | `string` | `str` | `NSelect` + TODO | same |
| `ForeignKeyField` | `number` | `int` | `NSelect` + TODO | same |

## i18n naming

- Module CN name: prompted on `init`, used as `route.<module>` / `page.<module>` top-level
- Model CN name: class docstring (`"""Warehouse"""`) or `Meta.table_description`
- Field CN name: `description="..."`, **truncated to first Chinese / English period**
  - `description="Warehouse code. Globally unique"` → `Warehouse code`
  - empty / missing → falls back to field name

## Module layering & file responsibilities

```
app/business/inventory/
├── models.py           # Tortoise models — only schema
├── schemas.py          # Pydantic — request / response DTO
├── controllers.py      # CRUDBase instances — single-resource CRUD entry
├── services.py         # business logic — cross-resource orchestration, transactions, cache
├── init_data.py        # menu / role / seed declarations (idempotent)
└── api/
    ├── __init__.py     # aggregates sub-routers
    └── manage.py       # admin endpoints (CRUDRouter + custom endpoints)
```

| Layer | Write | Don't write |
|---|---|---|
| `models.py` | columns, indexes, relations | business validation, default-value logic (use schema / service) |
| `schemas.py` | `XxxCreate / XxxUpdate / XxxSearch`, field-level validation | cross-resource logic |
| `controllers.py` | `xxx_controller = CRUDBase(model=Xxx)` | multi-model orchestration, transactions |
| `services.py` | transactions, cross-model, Redis, audit | HTTP (Request / Response) |
| `api/*.py` | URL wiring, DTO validation, permissions | actual business logic (call service) |

## CRUD practices

### Use `CRUDRouter` for the standard 6

`app/core/router.py`'s `CRUDRouter` factory generates per resource:

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/{prefix}/search` | paginated search; body = `XxxSearch` |
| `GET` | `/{prefix}/{item_id}` | single |
| `POST` | `/{prefix}` | create |
| `PATCH` | `/{prefix}/{item_id}` | update |
| `DELETE` | `/{prefix}/{item_id}` | delete one |
| `DELETE` | `/{prefix}` | batch delete (body: `{ids: [...]}`) |

Generated `api/manage.py` skeleton:

```python
from app.business.inventory.controllers import warehouse_controller
from app.business.inventory.schemas import WarehouseCreate, WarehouseSearch, WarehouseUpdate
from app.utils import CRUDRouter, DependPermission, SearchFieldConfig

warehouse_crud = CRUDRouter(
    prefix="/warehouses",
    controller=warehouse_controller,
    create_schema=WarehouseCreate,
    update_schema=WarehouseUpdate,
    list_schema=WarehouseSearch,
    search_fields=SearchFieldConfig(
        contains_fields=["name", "code"],
        exact_fields=["status"],
    ),
    summary_prefix="Warehouse",
)

router = APIRouter(prefix="/inventory", tags=["inventory"], dependencies=[DependPermission])
router.include_router(warehouse_crud.router)
```

### Override a route

When `list` needs join / extra fields, use `@crud.override("...")`:

```python
@warehouse_crud.override("list")
async def _list_warehouses(obj_in: WarehouseSearch):
    q = warehouse_controller.build_search(
        obj_in, contains_fields=["name"], exact_fields=["status"]
    )
    total, items = await warehouse_controller.list(
        page=obj_in.current,
        page_size=obj_in.size,
        search=q,
        order=["-id"],
        prefetch_related=["products"],
    )
    records = [await item.to_dict() for item in items]
    for r, item in zip(records, items):
        r["productCount"] = len(item.products)
    return SuccessExtra(data={"records": records}, total=total, current=obj_in.current, size=obj_in.size)
```

Overrideable names: `list / get / create / update / delete / batch_delete`.

### Add collection / instance actions

Endpoints beyond the standard 6 (e.g. `POST /warehouses/batch-offline`, `GET /warehouses/{id}/stats`) go directly on `router`, **not** through `CRUDRouter`:

```python
@router.get("/warehouses/stats", summary="Warehouse stats")
async def warehouse_stats():
    data = await service_list_warehouse_stats()  # business logic in service
    return Success(data=data)
```

### Transactions / cross-table writes go in `services.py`

```python
from tortoise.transactions import in_transaction
from app.utils import get_db_conn

async def create_product_with_stock(...):
    async with in_transaction(get_db_conn(Product)):
        product = await product_controller.create(obj_in=...)
        await stock_controller.create(obj_in={"product_id": product.id, "qty": 0})
    return product
```

`get_db_conn(Model)` returns the connection name — see [Standalone DB](/en/ops/database#business-module-standalone-database-advanced).

### Response wrappers

Always use one of these from `app.utils` — **never** raw dict:

| Class | Purpose | Typical |
|---|---|---|
| `Success(data=...)` | Single / non-paginated | get / create / update |
| `SuccessExtra(data=..., total=..., current=..., size=...)` | Paginated | list / search |
| `Fail(code=..., msg=...)` | Business failure | rule violation, permission denied |

## Permissions & menus: `init_data.py`

Each module's `init_data.py` declares menus, buttons, roles. Idempotent at startup:

```python
from app.system.services import ensure_menu, ensure_role, reconcile_menu_subtree

INVENTORY_MENU_CHILDREN = [
    {
        "menu_name": "Warehouse",
        "route_name": "inventory_warehouse",
        "route_path": "/inventory/warehouse",
        "component": "view.inventory_warehouse",
        "icon": "mdi:warehouse",
        "order": 1,
        "buttons": [
            {"button_code": "B_INV_CREATE", "button_desc": "Create warehouse"},
        ],
    },
]

INVENTORY_ROLE_SEEDS = [
    {
        "role_name": "Inventory admin",
        "role_code": "R_INV_MGR",
        "menus": ["home", "inventory", "inventory_warehouse"],
        "buttons": ["B_INV_CREATE"],
        "apis": [
            ("post", "/api/v1/business/inventory/warehouses"),
            ("post", "/api/v1/business/inventory/warehouses/search"),
        ],
    }
]


async def init():
    await ensure_menu(
        menu_name="Inventory",
        route_name="inventory",
        route_path="/inventory",
        icon="mdi:package-variant",
        order=9,
        children=INVENTORY_MENU_CHILDREN,
    )
    # Treat init_data as the single source of truth for this subtree
    await reconcile_menu_subtree(
        root_route="inventory",
        declared_route_names={"inventory_warehouse"},
        declared_button_codes={"B_INV_CREATE"},
    )
    for role in INVENTORY_ROLE_SEEDS:
        await ensure_role(**role)
```

**Key rules**:

- `ensure_menu()` / `ensure_role()` are **upserts** — safe to re-run
- After `reconcile_menu_subtree()`, the subtree is in IaC mode — Web-UI-created menus get reaped on next restart
- Removing a role from the seed does **not** delete the `Role` row (use a migration)

See [Startup init & reconciliation](/en/develop/init-data).

## Removing a module

Just `rm -rf app/business/<module>/`. autodiscover will skip it next time.

> **Note**: tables are not auto-dropped. Drop them manually or write a migration.

## See also

- [CRUDBase API](/en/develop/crud)
- [API conventions](/en/develop/api)
- [Startup init & reconciliation](/en/develop/init-data)
- [Switching DB](/en/ops/database)
- [Commands](/en/reference/commands)
