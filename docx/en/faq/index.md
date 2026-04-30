# FAQ

Grouped by scenario: startup, modules, permissions, routing, API IDs, and deployment.

## Startup & install

### `python run.py` says "no such table"

Tables are **not** auto-created at startup. First-time setup:

```bash
make initdb        # equivalent to tortoise init-db + first-time seeds
# or
make mm            # makemigrations + migrate
```

For ongoing model changes, use `make mm`. See [Commands](/en/reference/commands).

### Redis connection fails

```
redis-cli ping     # should return PONG
```

Or temporarily point to a local instance:

```dotenv
REDIS_URL=redis://localhost:6379/0
```

### Port already in use

Backend: 9999, frontend: 9527, Nginx: 1880. Adjust in `run.py` or `web/vite.config.ts`.

## Module development

### My manually-created menus / buttons disappeared after restart

Your `init_data.py` calls [`reconcile_menu_subtree(...)`](/en/develop/init-data) — that subtree is now in IaC mode and **only** menus / buttons declared in `init_data.py` survive. Web-UI-created entries are reaped on every restart.

If a subtree needs to allow user-created menus, **don't** call `reconcile_menu_subtree` on it.

### Startup logs show `ensure_role 'XXX': missing apis [...]`

The declared `(method, path)` no longer exists in the `Api` table. Common causes:

- A route was renamed / removed but the role seed `apis` list wasn't updated
- Typo (note method is lowercase: `"post"` not `"POST"`)

**Fix on sight** — otherwise the role's permission silently drops. See [Init data / drift warnings](/en/develop/init-data).

### I removed a role from init_data but it's still in the DB

`ensure_role` is upsert-only — it does **not** delete what's gone. Removal goes through a migration:

```python
# migrations/app_system/
async def upgrade(db):
    await db.execute_query("DELETE FROM roles WHERE role_code = 'R_OLD'")
```

Same applies to business seed data. This is intentional — auto-deletion has surprising cascades.

### My new business module's routes aren't mounted

Check startup logs:

```
Business: module 'inventory' discovered but has no api.py or api/ package — routes will not be registered
```

Add `api/__init__.py` that exports `router: APIRouter`.

```
Business: module 'inventory' api module does not export a valid 'router' (APIRouter) object
```

Make sure `api/__init__.py` actually has `router = APIRouter()` (or assigns it from a sub-router).

See [Autodiscover / common drift](/en/develop/autodiscover).

### Temporarily disable a business module

```bash
mv app/business/inventory app/business/_inventory
```

`autodiscover` skips directories starting with `_`.

### CLI-generated code has `// TODO`

Foreign keys / custom enums can't be auto-resolved into dropdown sources. Search the codebase for TODO and fill in the `options` data source (typically a `fetchGetXxxList` API call).

## Permissions

### I changed a role / menu but the user still has stale permissions

Permissions live in Redis cache. After CUD, refresh:

```python
from app.core.cache import load_role_permissions, load_user_roles

await load_role_permissions(redis, role_code="R_HR_ADMIN")
await load_user_roles(redis, user_id=123)
```

Or just restart — `refresh_all_cache` runs at startup.

### I revoked a user but their old token still works

After password change / forced logout:

```python
from app.system.services.auth import invalidate_user_session
await invalidate_user_session(redis, user_id)
```

This does `INCR token_version:{uid}`. Old tokens fail with `2106 SESSION_INVALIDATED` on next request. See [Auth / token_version](/en/develop/auth).

### Permission denied (`2201`) but the role is granted the menu

Menu and API are **two separate** dimensions. Role seeds must grant **both**:

```python
await ensure_role(
    role_code="R_HR_ADMIN",
    menus=[..., "hr_employee"],
    apis=[
        ("post", "/api/v1/business/hr/employees/search"),
        ("post", "/api/v1/business/hr/employees"),
    ],
)
```

### A department manager can see the entire company's data

The seed didn't declare `data_scope` explicitly. The model default is `all` = full access.

```python
{
    "role_code": "R_DEPT_MGR",
    "data_scope": DataScopeType.department,    # ← required
}
```

See [Data scope](/en/develop/data-scope).

## Routing (frontend)

### Editing `.env` doesn't take effect

Restart the Vite dev server.

### Route doesn't show in the menu

Check `hide_in_menu=True` on the menu, or that the current role doesn't have the `route_name` in its `menus`.

### Static vs dynamic routing

- `VITE_AUTH_ROUTE_MODE=static` — frontend defines routes, filtered by `roles` meta
- `VITE_AUTH_ROUTE_MODE=dynamic` (default) — backend issues per-user routes via `GET /api/v1/route/user-routes`

### CORS error

Dev: Vite proxy (`vite.config.ts` `server.proxy`). Prod: Nginx reverse proxy (see [Deployment](/en/ops/deployment)).

### Production 404

Make sure Nginx has `try_files $uri $uri/ /index.html;` — otherwise refreshing nested routes 404s.

### Vue "multi-root template" error

Page transitions use `<Transition>` which requires a single root:

```vue
<template>
  <div>...</div>     <!-- ✅ -->
</template>
```

## API IDs

### Frontend gets ID like `Yc7vN3kE`, not a number

That's a [sqid](/en/develop/sqids) — public-facing IDs are sqids. Frontend doesn't decode; just send it back as-is and the backend (`SqidPath` / `SqidId`) decodes automatically.

### Tests passed by sending numeric IDs?

`SqidId._sqid_to_int` accepts int, numeric string, and sqid during the migration period. Tighten in source after migration completes.

### After deploy, all external sqid links broke

`SECRET_KEY` was rotated — sqid alphabet derives from `SECRET_KEY`. See [Sqids / rotating SECRET_KEY](/en/develop/sqids).

## Deployment

### Every request gets banned by guard inside the container

Deployed behind Nginx without proxy-headers — all requests look like they're from the Nginx container's IP. Fix:

```dotenv
PROXY_HEADERS_ENABLED=true
TRUSTED_HOSTS=["10.0.0.0/8"]
```

### How do I unblock an IP from guard

```bash
redis-cli --scan --pattern "fastapi_guard:*" | xargs redis-cli del
```

Or temporarily set `GUARD_ENABLED=false` and restart.

### Switched DB and got "module not found: asyncpg"

The driver isn't installed:

```bash
uv add asyncpg          # postgres
uv add asyncmy          # mysql
uv add asyncodbc        # mssql
```

See [Switching DB / drivers](/en/ops/database).

### Multi-worker startup duplicates seeds?

No — `_run_init_data` uses Redis lock `app:init_lock` to elect a leader. Only the leader runs init.

```bash
redis-cli get app:init_done    # should be "1"
```

## Docker

### View backend logs

```bash
make logs                        # all
make logs SVC=app                # backend only; SVC=nginx|redis, TAIL=N for line count
docker compose logs -f app       # equivalent native form
```

### Update deployment

```bash
git pull
make down && make up
```

### Wrong timezone in container

Tortoise defaults to `use_tz=False, timezone=Asia/Shanghai`. For UTC: change `TORTOISE_ORM["use_tz"]=True` and `timezone="UTC"` in `app/core/config.py`.
