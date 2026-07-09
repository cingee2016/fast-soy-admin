# Data Scope

RBAC controls "which menus / endpoints / buttons you can use"; data scope controls "which **rows** you can see" — e.g. tenant admins see their tenant's customers, project owners see their project's orders, and regular users see only themselves.

Source: `app/core/data_scope.py`.

## Four scopes

| Value | Meaning | Typical role |
|---|---|---|
| `all` | All rows; no filter | Inventory director / system admin |
| `scope` | Current business scope | tenant admin / org lead / project owner |
| `self` | Only your own | regular product |
| `custom` | Reserved; currently falls back to `self` | — |

`R_SUPER` and `data_scope=all` skip filtering entirely.

## Multi-role: most permissive wins

A user can hold multiple roles (e.g. platform admin + tenant admin). The final scope is the **most permissive**:

```
all  >  scope  >  self  >  custom
```

Implementation `get_current_data_scope(redis)`: iterate `CTX_ROLE_CODES`, read each `role:{code}:data_scope`, return the highest (lowest priority number).

## Role seeds must be explicit

The model defaults `data_scope=all`, so omitting it on `ensure_role()` makes the role "all-visible". **Always declare it explicitly** in business role seeds:

```python
BIZ_ROLE_SEEDS = [
    {
        "role_code": "R_PLATFORM_ADMIN",
        "data_scope": DataScopeType.all,             # explicit all
        ...
    },
    {
        "role_code": "R_TENANT_ADMIN",
        "data_scope": DataScopeType.scope,           # current business scope
        ...
    },
    {
        "role_code": "R_USER",
        "data_scope": DataScopeType.self_,           # note: Python keyword → self_
        ...
    },
]
```

> `ensure_role` doesn't enforce this (omitting keeps existing) — relies on code review. Forgetting it makes scoped business roles see everything.

## Use it in business endpoints

```python
from app.utils import CTX_USER_ID, build_scope_filter, get_current_data_scope

async def list_products_with_relations(search_in: ProductSearch, redis=None):
    q = product_controller.build_search(search_in, contains_fields=[...])

    scope = await get_current_data_scope(redis)
    scope_q = build_scope_filter(
        scope=scope,
        user_id=CTX_USER_ID.get(),
        scope_id=get_current_scope_id(),       # module-local ctx helper
        user_id_field="user_id",               # user column in your model
        scope_id_field="tenant_id",            # business-scope column in your model
    )
    total, products = await product_controller.list(..., search=q & scope_q)
    return total, records
```

`build_scope_filter`:

| Input | scope-matched behavior |
|---|---|
| `is_super_admin()` or `scope == "all"` | empty `Q()`, no filter |
| `scope == "scope"` and `scope_id` not None | `Q(<scope_id_field>=...)` |
| Otherwise (incl. `self` / `custom`) | `Q(user_id=...)` |

Column names are configurable via `user_id_field` / `scope_id_field`.

## How a module provides scope_id

A module typically uses a local ContextVar + dependency to inject the current user's business-scope id. That scope can be a tenant, organization, project, store, etc.; the system no longer requires a fixed warehouse field:

```python
# app/business/crm/ctx.py
import contextvars

_CTX_SCOPE_ID: contextvars.ContextVar[int | None] = contextvars.ContextVar("crm_scope_id", default=None)

def get_current_scope_id() -> int | None:
    return _CTX_SCOPE_ID.get()

def set_current_scope_id(scope_id: int | None) -> None:
    _CTX_SCOPE_ID.set(scope_id)
```

```python
# app/business/crm/dependency.py
from fastapi import Depends
from app.utils import DependAuth, get_current_user_id

async def _bind_tenant_context(_: User = DependAuth):
    member = await TenantMember.filter(user_id=get_current_user_id()).first()
    if member:
        set_current_scope_id(member.tenant_id)

DependTenant = Depends(_bind_tenant_context)
```

```python
# app/business/crm/api/__init__.py
router = APIRouter(prefix="/crm", dependencies=[DependPermission, DependTenant])
```

Now every CRM endpoint sees the right `get_current_scope_id()` value when entering services.

## Redis fallback

`get_current_data_scope(redis=None)` falls back to a DB query (`Role.filter(role_code__in=...)`). Production Redis outages don't break data scope — just slower.

## Which resources should be scoped

Not every table needs scope. Rule of thumb:

- **Strong scope**: orders, customers, tickets — anything with personal / business-scope ownership
- **Not needed**: dictionaries, menus, roles, buttons, system config (RBAC suffices)
- **Be careful**: log tables (limiting by `actor_id` may hide audit trails from admins)

## Relationship with `CRUDRouter`

`CRUDRouter`'s default `list` route doesn't add scope (it doesn't know your column names). For scoped resources, `@override("list")`:

```python
@product_crud.override("list")
async def _list(obj_in: ProductSearch, request: Request):
    total, records = await list_products_with_relations(obj_in, redis=request.app.state.redis)
    return SuccessExtra(data={"records": records}, total=total, current=obj_in.current, size=obj_in.size)
```

The CLI can generate this override directly:

```bash
uv run python -m app.cli crud crm --models Customer --data-scope Customer:owner_id,tenant_id
```

Generated code passes `user_id_field` / `scope_id_field` into `build_scope_filter()` and emits an `_get_scope_id()` hook. Scope-level permission should wire that hook to the module's business context; until then, the `scope` tier follows `build_scope_filter()` and falls back to `self`.

## See also

- [RBAC](/en/develop/rbac)
- [Data scope](/en/develop/data-scope)
- [Cache](/en/ops/cache) — `role:{code}:data_scope`
