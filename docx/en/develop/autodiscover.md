# Business Module Autodiscover

`app/core/autodiscover.py` scans `app/business/*/` at startup and loads each module's models, routes, init function, and standalone DB config. **Business modules need no manual registration**.

## Recognition rules

A subdirectory under `app/business/` is treated as a business module if it:

- has `__init__.py`
- doesn't start with `_` (`_internal/`, `__pycache__/` are skipped)

## What a module can provide

| File | Loaded at | Behavior |
|---|---|---|
| `models.py` or `models/__init__.py` | `Settings` construction | added to `TORTOISE_ORM["apps"]["app_system"].models` (or its own app) |
| `api/__init__.py` or `api.py` (must export `router: APIRouter`) | `create_app()` | `include_router` mounted under `/api/v1/business/` |
| `init_data.py` (must export `async def init()`) | `lifespan` (leader worker only) | runs after system init, before `refresh_all_cache` |
| `config.py` (exports a Settings instance with `DB_URL`) | `Settings` construction | registers a separate Tortoise connection + app (only if `DB_URL` differs from main) |

## Standard layout

Mirrors `app/business/hr/`:

```
app/business/<name>/
├── __init__.py
├── config.py          # optional — BIZ_SETTINGS (per-module Pydantic Settings)
├── ctx.py             # optional — module ContextVars
├── dependency.py      # optional — module FastAPI dependencies
├── models.py          # Tortoise models
├── schemas.py         # Pydantic schemas
├── controllers.py     # CRUDBase subclasses
├── services.py        # multi-model orchestration / cache / FSM
├── cache_utils.py     # optional — cache invalidation helpers
├── init_data.py       # async def init()
└── api/
    ├── __init__.py    # must export router
    ├── manage.py
    ├── dept.py
    └── my.py
```

## Startup load order

```
Settings._build_tortoise_orm()
  ├─ discover_business_models()           # collect app.business.*.models
  └─ discover_business_db_configs()       # find config.py with DB_URL
       │
       ▼
  TORTOISE_ORM = {
    "connections": {
      "conn_system":  APP_SETTINGS.DB_URL,
      "conn_billing": "postgres://...",   # only if a module declared standalone DB
    },
    "apps": {
      "app_system":  {"models": [..., "app.business.hr.models", ...], "default_connection": "conn_system"},
      "app_billing": {"models": ["app.business.billing.models"], "default_connection": "conn_billing"},
    },
  }

create_app()
  ├─ register_db(app)                      # the TORTOISE_ORM above takes effect
  ├─ register_routers(app, prefix="/api")  # /api/v1/auth, /api/v1/system-manage/*, ...
  └─ discover_business_routers()           # /api/v1/business/<name>/*

lifespan(app)
  └─ leader runs init_data.init() for each business
```

## Common drift & troubleshooting

### Module discovered but no routes mounted

Startup log:

```
Business: module 'inventory' discovered but has no api.py or api/ package — routes will not be registered
```

`app/business/inventory/__init__.py` exists but no `api.py` / `api/__init__.py`. Either add the api or temporarily delete `__init__.py` to disable the module.

### `api` module doesn't export router

```
Business: module 'inventory' api module does not export a valid 'router' (APIRouter) object
```

`api/__init__.py` must have:

```python
from .manage import router as manage_router
# ...
router = APIRouter()
router.include_router(manage_router)
```

### Business model doesn't participate in migrations

No model registration log at startup, but the API errors with "no such table". Check:

- Is the file named `model.py` (missing `s`)?
- Or you're using a `models/` package without `__init__.py`?

### Temporarily disable a module

Prefix with `_` to disable without code changes:

```bash
mv app/business/inventory app/business/_inventory
```

## Business module standalone DB

The module's `config.py`:

```python
# app/business/billing/config.py
from pydantic_settings import BaseSettings

class BillingSettings(BaseSettings):
    DB_URL: str = "postgres://billing-host:5432/billing"

    model_config = {"env_file": ".env", "extra": "ignore", "env_prefix": "BILLING_"}

BIZ_SETTINGS = BillingSettings()
```

`discover_business_db_configs` finds `BIZ_SETTINGS.DB_URL` — if different from main, registers a separate connection `conn_billing` + a separate app `app_billing`.

Cross-model transactions use `get_db_conn(Model)`:

```python
async with in_transaction(get_db_conn(Invoice)):  # auto-picks conn_billing
    await Invoice.create(...)
```

See [Switching DB / standalone DB](/en/ops/database#business-module-standalone-database-advanced).

## init_data.init() execution

- Only the leader worker runs it (Redis-coordinated)
- Order: alphabetical by module name (`hr` < `inventory` < `notify`)
- A single module exception **doesn't** affect others — caught and recorded in `app.state.init_errors`
- The function should be idempotent (use the `ensure_*` helpers)

See [Init data](/en/develop/init-data).

## End note: module boundaries

Autodiscover is what makes "business modules" pluggable. The complementary strong rules:

- A business module **doesn't reverse-import** other business modules (`app.business.crm.*` cannot import `app.business.hr.*`)
- The business import facade is [`app.utils`](/en/reference/utils)
- Cross-module wiring goes through the [event bus](/en/develop/events)

Violating these still works at runtime — but the modular value autodiscover provides is gone.

## See also

- [Development guide](/en/getting-started/workflow) — create a new module via the CLI
- [Init data](/en/develop/init-data) — how `init()` runs and reconciles
- [HR module](/en/develop/business-hr) — sample business module
