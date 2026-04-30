# Architecture

## Overview

```
                ┌──────────────────────────────────────────────┐
                │              FastAPI App                      │
                │  ┌──────────────────────────────────────┐    │
                │  │  Middleware: CORS / RequestID /      │    │
                │  │  BackgroundTask / Guard / Radar      │    │
                │  └──────────────────────────────────────┘    │
                │                                                │
                │  /api/v1/auth                  (system)        │
                │  /api/v1/route                 (system)        │
                │  /api/v1/system-manage/*       (system)        │
                │  /api/v1/business/<module>/*   (business)      │
                │                                                │
                │   api → services → controllers → models        │
                └──────────────────────────────────────────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
         Tortoise ORM           Redis             Sqids/JWT
         (SQLite/PG/MySQL)      (cache + lock)    (encode/sign)
```

## Module boundaries

| Package | Responsibility | Allowed dependencies |
|---|---|---|
| `app/core/` | framework infrastructure (no business) | doesn't depend on system / business |
| `app/system/` | built-in modules (auth, RBAC, users, menus, APIs, dictionary) | only `app/core/` |
| `app/business/<x>/` | business modules (HR / CRM / Inventory ...) | `app/utils` (transitively core/system); **never** sibling business modules |
| `app/utils/` | stable public facade for business code | re-exports `app/core/*` and a few `app/system/security` symbols |
| `app/cli/` | code generators (init/gen/gen-web/initdb) | offline-only, no runtime impact |

Business code should never `from app.system.xxx import ...` (except services system explicitly exposes — `ensure_menu` / `ensure_role`). For cross-business communication use the [event bus](/en/develop/events).

## Request lifecycle

1. **Inbound middleware** (`app/core/middlewares.py` + `make_middlewares()`)
   - `CORSMiddleware`
   - `PrettyErrorsMiddleware` — pretty exception output
   - `BackgroundTaskMiddleware` — injects FastAPI's `BackgroundTasks` into `CTX_BG_TASKS`
   - `RequestIDMiddleware` — injects `X-Request-ID` to response headers and `CTX_X_REQUEST_ID`
   - `RadarMiddleware` (conditional) — captures request / SQL / exception to Radar
   - [`fastapi-guard`](https://fastapi-guard.com/) (conditional) — rate limit / auto-ban
2. **Routing** — business routes uniformly under `/api/v1/business/<name>`; system routes under `/api/v1/{auth,route,system-manage}`
3. **Dependency injection**
   - `DependAuth` — JWT decode → check token version → load user + role/button permissions into ContextVars
   - `DependPermission` — on top of `DependAuth`, exact `(method, path)` match against `role.apis`
   - `require_buttons(...)` / `require_roles(...)` — factory dependencies, attach as needed
4. **Business logic**
   - `api/` only wires; rules live in `services/` and `controllers/`
5. **Response**
   - Always return `Success` / `SuccessExtra` / `Fail` (`JSONResponse` subclasses, auto camelCase)

## Startup lifecycle

```
create_app()
  ├─ register_db(app)                  # Tortoise.init(config=TORTOISE_ORM)
  ├─ register_exceptions(app)          # BizError / DoesNotExist / IntegrityError / ValidationError handlers
  ├─ register_routers(app, prefix="/api")   # system /api/v1/...
  ├─ discover_business_routers()       # /api/v1/business/<name>/...
  └─ setup_radar(app)                  # optional

lifespan(app)
  ├─ init_redis() → app.state.redis
  ├─ FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
  ├─ delete _INIT_LOCK_KEY / _INIT_DONE_KEY
  ├─ _run_init_data(app)               # leader-only with multi-worker
  │    ├─ init_menus()                 # system menu seeds (only when Menu table is empty)
  │    ├─ refresh_api_list()           # FastAPI routes ↔ Api table reconciliation
  │    ├─ init_users()                 # system roles + default users + dictionary
  │    ├─ for each business init():    # business modules' init_data.init()
  │    └─ refresh_all_cache()          # role permissions / constant routes → Redis
  ├─ startup_radar()                   # optional
  └─ yield
       ↓ shutdown
  └─ close_redis()
```

For semantics see [Startup init & reconciliation](/en/develop/init-data).

## RBAC data model

```
User ←M2M→ Role ←M2M→ Menu      (frontend-visible routes)
                ←M2M→ Button    (in-page actionable buttons)
                ←M2M→ Api       (callable backend endpoints)
                FK    Menu      (role's default home page; by_role_home)
              field   data_scope (row-level scope: all / department / self / custom)
```

- The super-admin role `R_SUPER` (`app.core.constants.SUPER_ADMIN_ROLE`) bypasses every check
- API permissions are auto-managed by `refresh_api_list()` (full reconciliation by `(method, path)`)
- Menus / buttons are declared per module via `ensure_menu()`, optionally with `reconcile_menu_subtree()` for IaC
- Button code convention: `B_<MODULE>_<RESOURCE>_<ACTION>` (e.g. `B_HR_EMP_CREATE`)
- See [Auth](/en/develop/auth) / [Data scope](/en/develop/data-scope)

## Multi-worker startup

Production typically runs 4 granian workers. They coordinate via Redis lock `app:init_lock`:

- The leader (`SET app:init_lock 1 NX EX 120` winner) runs the full init, then `SET app:init_done 1 EX 120`
- Other workers poll `app:init_done` (max wait 150s)
- Before each process start, the leader `DEL`s both keys, so init really runs on every restart

## Multi-database connections

- By default all models live on `conn_system`
- A business module can declare its own `DB_URL` in `config.py`, which autodiscover registers as `conn_<biz>` with a separate Tortoise app
- Use `get_db_conn(Model)` for cross-model transactions; never hard-code the connection name
- See [Database / standalone DB](/en/ops/database#business-module-standalone-database-advanced)

## Cache model

| Data | Redis Key | TTL | Writer |
|---|---|---|---|
| Constant routes | `constant_routes` | forever | `refresh_all_cache` |
| Role menu IDs | `role:{code}:menus` | forever | `load_role_permissions` |
| Role APIs | `role:{code}:apis` | forever | same |
| Role buttons | `role:{code}:buttons` | forever | same |
| Role data scope | `role:{code}:data_scope` | forever | same |
| User roles | `user:{uid}:roles` | forever | `load_user_roles` |
| User home | `user:{uid}:role_home` | forever | same |
| Token version | `token_version:{uid}` | forever | password change / impersonate |
| Business-local | per module | per module | per module |

See [Cache](/en/ops/cache).

## Where to next

- [Core / CRUDRouter](/en/develop/crud-router)
- [Core / Schema base](/en/develop/schema)
- [Auth](/en/develop/auth)
- [Startup init & reconciliation](/en/develop/init-data)
