# Cache

Three backend caching scenarios:

| Scenario | Tool | Refresh trigger |
|---|---|---|
| System "permission hot data" (role permissions, constant routes, token version) | dedicated functions in `app/core/cache.py` | startup `refresh_all_cache` + incremental on CUD |
| Per-endpoint "memoize result" | `fastapi-cache2` decorator | TTL expiry |
| Module-local "small hotspots" (dict options, stats) | module's `cache_utils.py` + raw Redis | active invalidation on data change |

The Redis client is at `app.state.redis` (`redis.asyncio.Redis`); access via `request.app.state.redis`.

## System permission cache

`app/core/cache.py` maintains:

| Key | Content | Writer |
|---|---|---|
| `constant_routes` | constant route JSON | `load_constant_routes` |
| `role:{code}:menus` | menu IDs | `load_role_permissions` |
| `role:{code}:apis` | `[{method, path, status}]` | same |
| `role:{code}:buttons` | button codes | same |
| `role:{code}:data_scope` | `all` / `department` / `self` / `custom` | same |
| `user:{uid}:roles` | role codes | `load_user_roles` |
| `user:{uid}:role_home` | route name of home page | same |
| `token_version:{uid}` | int (INCR) | `invalidate_user_session` etc. |

Read (used in `DependAuth` / `DependPermission`):

```python
from app.core.cache import (
    get_constant_routes,
    get_role_apis, get_role_menu_ids,
    get_user_role_codes, get_user_button_codes, get_user_role_home,
)
```

Startup `refresh_all_cache(redis)` loads everything. After CUD, **incrementally** refresh — e.g. modifying a role: `await load_role_permissions(redis, role_code="R_HR_ADMIN")` — otherwise users see stale permissions.

### Redis fallback

If `DependAuth` fails to read `get_user_role_codes / get_user_button_codes`, it falls back to DB (`user.fetch_related("by_user_roles")`) with a WARNING log:

```
Redis unavailable, loading permissions from database for user 123
```

`DependPermission` and `data_scope` have the same fallback. Production Redis outages don't break auth — they just slow it down.

## Module-local cache

For module hotspots (stats / options / aggregations), read/write Redis directly. The snippet below illustrates the pattern (not actual repository code):

```python
# app/business/<module>/services.py
import json

STATS_KEY = "<module>_<resource>:all"
STATS_TTL = 5 * 60  # 5 minutes

async def get_stats(redis):
    cached = await redis.get(STATS_KEY)
    if cached:
        return json.loads(cached)

    rows = await Model.annotate(...).group_by("xxx_id").values(...)
    await redis.set(STATS_KEY, json.dumps(rows, ensure_ascii=False), ex=STATS_TTL)
    return rows
```

**Actively invalidate** on data change:

```python
# app/business/<module>/cache_utils.py (if needed)
async def invalidate_stats(redis):
    await redis.delete(STATS_KEY)
```

A live in-repo reference using the same pattern is the dictionary-options cache (`app/system/api/dictionary.py`):

```python
@router.get("/dictionaries/{dict_type}/options")
async def get_dict_options(dict_type: str, request: Request):
    cache_key = f"dict_options:{dict_type}"
    cached = await request.app.state.redis.get(cache_key)
    if cached:
        return Success(data=json.loads(cached))
    ...
```

## fastapi-cache2

Already initialized at startup:

```python
FastAPICache.init(RedisBackend(_app.state.redis), prefix="fastapi-cache")
```

To memoize an entire endpoint, use `@cache(...)`:

```python
from fastapi_cache.decorator import cache

@router.get("/heavy-report")
@cache(expire=60, namespace="reports")
async def _heavy_report(): ...
```

::: warning Don't blanket-cache paginated / multi-param endpoints
The cache key is parameter-derived; many filter combinations easily blow Redis. For business-key-scoped hotspots, use the manual pattern above.
:::

## Cache key naming

- System permission: `role:{code}:*` / `user:{uid}:*` (no module prefix)
- Module-local: `<module>_<resource>:<scope>` (module prefix required to avoid collisions)
  - Examples: `dict_options:tag_category`, `crm_lead_cnt:dept_42`
- Lock / coordination: `app:<purpose>` (`app:init_lock`, `app:init_done`)

## Multi-worker init lock

`app/__init__.py`'s `_run_init_data` uses two keys:

| Key | Purpose | TTL |
|---|---|---|
| `app:init_lock` | leader election (`SET NX EX 120`) | 120s |
| `app:init_done` | leader-completed signal | 120s |

The leader `DEL`s both before each start, so init really runs every restart — that's why `reconcile_menu_subtree` works correctly.

## Debug tricks

```bash
# Inspect role permission cache
redis-cli get "role:R_HR_ADMIN:apis" | jq

# Force-invalidate a user session (kill all old tokens)
redis-cli incr "token_version:123"

# Clear all dictionary caches (dictionary.py invalidate_dict_cache does this too)
redis-cli --scan --pattern "dict_options:*" | xargs redis-cli del

# Inspect startup lock
redis-cli get "app:init_done"
```

## See also

- [RBAC](/en/develop/rbac) — how the permission cache is used
- [Auth](/en/develop/auth) — token_version
- [Init data](/en/develop/init-data) — when `refresh_all_cache` runs
