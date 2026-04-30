# RBAC (menus / APIs / buttons)

Classic RBAC: User ↔ Role ↔ {Menu / Button / API}; `R_SUPER` bypasses every check. This page covers the data model and runtime; **JWT / invalidation** is in [Auth](/en/develop/auth); **row-level scope** is in [Data scope](/en/develop/data-scope).

## Relationships

```
User ──M2M─→ Role ──M2M─→ Menu      (frontend-visible routes)
                  ──M2M─→ Button    (in-page actionable buttons)
                  ──M2M─→ Api       (callable backend endpoints)
                  ──FK──→ Menu      (default landing page)
                  field   data_scope
```

Source models: `app/system/models/admin.py`.

## Three permission dimensions

| Dimension | Controls | Declared by | Checked when |
|---|---|---|---|
| **Menu** | Frontend-visible route tree | `init_data.py`'s `ensure_menu` | `GET /api/v1/route/user-routes` filters by role |
| **API** | Callable backend endpoint | `refresh_api_list` auto-reconciles from FastAPI routes | `DependPermission` per request |
| **Button** | In-page action | `init_data.py`'s `ensure_menu(buttons=...)` | `require_buttons` (backend); `hasAuth(...)` (frontend) |

> An action typically needs both "button + API". Hiding only the button isn't safe; only blocking the API hurts UX.

## Super admin

- Code `R_SUPER` (`app.core.constants.SUPER_ADMIN_ROLE`)
- `DependPermission` / `require_buttons` / `require_roles` short-circuit on `R_SUPER`
- `_ensure_super_role()` re-attaches every non-constant menu + every button to this role on every startup

## Menus and buttons: declarative

Each module declares menus (with their buttons) in its `init_data.py`; `ensure_menu` upserts into `Menu` / `Button`:

```python
HR_MENU_CHILDREN = [
    {
        "menu_name": "Employees",
        "route_name": "hr_employee",
        "route_path": "/hr/employee",
        "buttons": [
            {"button_code": "B_HR_EMP_CREATE", "button_desc": "create employee"},
            {"button_code": "B_HR_EMP_EDIT",   "button_desc": "edit employee"},
            {"button_code": "B_HR_EMP_DELETE", "button_desc": "delete employee"},
            {"button_code": "B_HR_EMP_TRANSITION", "button_desc": "state transition"},
        ],
    },
]

await ensure_menu(menu_name="HR", route_name="hr", ..., children=HR_MENU_CHILDREN)
```

To "delete entries that are no longer in the seed", enable `reconcile_menu_subtree(root_route="hr", ...)` — the subtree enters IaC mode. See [Init data](/en/develop/init-data).

## Button naming convention

```
B_<MODULE>_<RESOURCE>_<ACTION>
```

| Example | Meaning |
|---|---|
| `B_HR_DEPT_CREATE` | HR / department / create |
| `B_HR_EMP_TRANSITION` | HR / employee / state transition |
| `B_INV_PRODUCT_DELETE` | Inventory / product / delete |

General rules:

- One button = one action category; **single delete + batch delete share one code** (HR does this)
- "Read list" doesn't need a button — menu visibility + API authorization are enough
- Truly cross-module buttons (rare) live in the system layer

## API: auto-reconciled

`refresh_api_list()` (`app/system/api/utils.py`) on every startup:

1. Lists all `APIRoute`s' `(method, path)`
2. Set-diffs against `Api` rows where `is_system=True`
3. Extras → DELETE + Radar warning ("API deleted")
4. Missing → INSERT
5. Existing → UPDATE summary / tags

Developers **never** maintain the `Api` table by hand — adding / removing / renaming routes auto-syncs.

`Api.status_type=disable` lets an admin temporarily disable an endpoint via Web UI; hits return `2200 API_DISABLED`.

## Role seed declaration

```python
from app.core.data_scope import DataScopeType
from app.system.services import ensure_role

await ensure_role(
    role_name="HR admin",
    role_code="R_HR_ADMIN",
    role_desc="HR specialist",
    home_route="hr_employee",
    data_scope=DataScopeType.all,
    menus=["home", "hr", "hr_department", "hr_employee", "hr_tag"],
    buttons=["B_HR_DEPT_CREATE", "B_HR_DEPT_EDIT", ...],
    apis=[
        ("post", "/api/v1/business/hr/employees/search"),
        ("post", "/api/v1/business/hr/employees"),
        ...
    ],
)
```

`ensure_role` does **clear-and-readd** for `menus / buttons / apis` (None=skip, []=clear, [...] = replace).

### Drift warnings

When a declared `route_name` / `button_code` / `(method, path)` doesn't exist in the DB:

```
ensure_role 'R_HR_ADMIN': missing apis [('post', '/api/v1/business/hr/old')] (route signature changed?)
```

**Fix on sight** — the seed is out of sync with the code. See [Init data / drift](/en/develop/init-data).

### data_scope must be explicit

Omitting `data_scope` on `ensure_role(...)` keeps the model default `all` — wrong for department managers / regular users. **Always set it explicitly** in business role seeds. See [Data scope](/en/develop/data-scope).

## Backend dependencies

```python
from app.utils import DependPermission, require_buttons, require_roles
```

| Dependency | Use | Failure code |
|---|---|---|
| `DependPermission` | Mount on a router group (`include_router(..., dependencies=[DependPermission])`) | `2200 / 2201` |
| `require_buttons("B_X", ...)` | any one | `2203` |
| `require_buttons(..., require_all=True)` | all required | `2202` |
| `require_roles("R_X", ...)` | any one | `2205` |
| `require_roles(..., require_all=True)` | all required | `2204` |

`R_SUPER` always passes. See [Auth / dependencies](/en/develop/auth#auth-dependencies).

## Frontend button gating

Button codes are delivered via `GET /api/v1/auth/user-info` (sourced from `CTX_BUTTON_CODES`; `R_SUPER` users get **all** codes). The frontend uses `hasAuth('B_HR_EMP_CREATE')` to decide whether to render a button — see [Frontend / Hooks / useTable / Pair with permission buttons](/en/frontend/hooks/use-table#pair-with-permission-buttons).

## Cache

| Redis Key | Content |
|---|---|
| `role:{code}:menus` | menu IDs |
| `role:{code}:apis` | `[{method, path, status}]` |
| `role:{code}:buttons` | button codes |
| `role:{code}:data_scope` | data scope |
| `user:{uid}:roles` | role codes |
| `user:{uid}:role_home` | route name of home page |

Write timing:

- Startup `refresh_all_cache(redis)` loads everything
- After role / user / menu CUD, the business calls `load_role_permissions(redis, role_code=...)` / `load_user_roles(redis, user_id=...)` to update incrementally

`DependAuth` / `DependPermission` read directly from Redis; on Redis failure they fall back to DB (with WARNING). See [Cache](/en/ops/cache).

## See also

- [Auth (JWT / token_version / impersonate)](/en/develop/auth)
- [Data scope](/en/develop/data-scope)
- [Init data](/en/develop/init-data)
- [Response codes 22xx](/en/reference/codes#22xx--authorization)
