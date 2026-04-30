# Data Scope

RBAC controls "which menus / endpoints / buttons you can use"; data scope controls "which **rows** you can see" — e.g. department managers see their department's employees, regular employees see only themselves.

Source: `app/core/data_scope.py`.

## Four scopes

| Value | Meaning | Typical role |
|---|---|---|
| `all` | All rows; no filter | HR director / system admin |
| `department` | Only your department | department manager |
| `self` | Only your own | regular employee |
| `custom` | Reserved; currently falls back to `self` | — |

`R_SUPER` and `data_scope=all` skip filtering entirely.

## Multi-role: most permissive wins

A user can hold multiple roles (e.g. HR director + department manager). The final scope is the **most permissive**:

```
all  >  department  >  self  >  custom
```

Implementation `get_current_data_scope(redis)`: iterate `CTX_ROLE_CODES`, read each `role:{code}:data_scope`, return the highest (lowest priority number).

## Role seeds must be explicit

The model defaults `data_scope=all`, so omitting it on `ensure_role()` makes the role "all-visible". **Always declare it explicitly** in business role seeds:

```python
HR_ROLE_SEEDS = [
    {
        "role_code": "R_HR_ADMIN",
        "data_scope": DataScopeType.all,             # explicit all
        ...
    },
    {
        "role_code": "R_DEPT_MGR",
        "data_scope": DataScopeType.department,      # explicit department
        ...
    },
    {
        "role_code": "R_USER",
        "data_scope": DataScopeType.self_,           # note: Python keyword → self_
        ...
    },
]
```

> `ensure_role` doesn't enforce this (omitting keeps existing) — relies on code review. Forgetting it makes department managers see the entire company.

## Use it in business endpoints

```python
from app.utils import CTX_USER_ID, build_scope_filter, get_current_data_scope

async def list_employees_with_relations(search_in: EmployeeSearch, redis=None):
    q = employee_controller.build_search(search_in, contains_fields=[...])

    scope = await get_current_data_scope(redis)
    scope_q = build_scope_filter(
        scope=scope,
        user_id=CTX_USER_ID.get(),
        department_id=get_department_id(),     # module-local ctx helper
        user_id_field="user_id",               # column name in your model
        dept_id_field="department_id",         # column name in your model
    )
    total, employees = await employee_controller.list(..., search=q & scope_q)
    return total, records
```

`build_scope_filter`:

| Input | scope-matched behavior |
|---|---|
| `is_super_admin()` or `scope == "all"` | empty `Q()`, no filter |
| `scope == "department"` and `department_id` not None | `Q(department_id=...)` |
| Otherwise (incl. `self` / `custom`) | `Q(user_id=...)` |

Column names are configurable via `user_id_field` / `dept_id_field`.

## How a module provides department_id

A module typically uses a local ContextVar + dependency to inject "current user's department id":

```python
# app/business/hr/ctx.py
import contextvars

_CTX_DEPT_ID: contextvars.ContextVar[int | None] = contextvars.ContextVar("hr_dept_id", default=None)

def get_department_id() -> int | None:
    return _CTX_DEPT_ID.get()

def set_department_id(dept_id: int | None) -> None:
    _CTX_DEPT_ID.set(dept_id)
```

```python
# app/business/hr/dependency.py
from fastapi import Depends
from app.utils import DependAuth, get_current_user_id

async def _bind_employee_context(_: User = DependAuth):
    emp = await Employee.filter(user_id=get_current_user_id()).first()
    if emp:
        await emp.fetch_related("department")
        set_department_id(emp.department_id)

DependEmployee = Depends(_bind_employee_context)
```

```python
# app/business/hr/api/__init__.py
router = APIRouter(prefix="/hr", dependencies=[DependPermission, DependEmployee])
```

Now every HR endpoint sees the right `get_department_id()` value when entering services.

## Redis fallback

`get_current_data_scope(redis=None)` falls back to a DB query (`Role.filter(role_code__in=...)`). Production Redis outages don't break data scope — just slower.

## Which resources should be scoped

Not every table needs scope. Rule of thumb:

- **Strong scope**: employee records, orders, customers — anything with personal / department ownership
- **Not needed**: dictionaries, menus, roles, buttons, system config (RBAC suffices)
- **Be careful**: log tables (limiting by `actor_id` may hide audit trails from admins)

## Relationship with `CRUDRouter`

`CRUDRouter`'s default `list` route doesn't add scope (it doesn't know your column names). For scoped resources, `@override("list")`:

```python
@emp_crud.override("list")
async def _list(obj_in: EmployeeSearch, request: Request):
    total, records = await list_employees_with_relations(obj_in, redis=request.app.state.redis)
    return SuccessExtra(data={"records": records}, total=total, current=obj_in.current, size=obj_in.size)
```

## See also

- [RBAC](/en/develop/rbac)
- [HR module (full row-level permission example)](/en/develop/business-hr)
- [Cache](/en/ops/cache) — `role:{code}:data_scope`
