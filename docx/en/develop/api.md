# API Conventions

All system / business endpoints share one enforced convention; deviations require discussion.

Full API reference: [Apidog](https://fast-soy-admin.apidog.io). This page covers **conventions** and a **key endpoint cheat sheet**.

## Route prefixes

| Prefix | Purpose |
|---|---|
| `/api/v1/auth` | Authentication (public) |
| `/api/v1/route` | Route delivery (constant routes / user routes) |
| `/api/v1/system-manage/*` | System modules (users / roles / menus / APIs / dictionary) |
| `/api/v1/business/<module>/*` | Business modules (autodiscovered) |

## Response format

All success responses are:

```json
{ "code": "0000", "msg": "OK", "data": { ... } }
```

Field naming is uniformly **camelCase** — `SchemaBase`'s `alias_generator=to_camel_case` handles it; `Model.to_dict()` outputs camelCase too. **Don't** return raw dicts; **don't** hand-roll snake_case.

For codes / frontend mapping see [Response codes](/en/reference/codes).

## Path & method

| Operation | Method + path | Body / Params |
|---|---|---|
| List / search | `POST /resources/search` | Body extends `PageQueryBase` |
| Single | `GET /resources/{id}` | — |
| Create | `POST /resources` | Body: `XxxCreate` |
| Update | `PATCH /resources/{id}` | Body: `XxxUpdate` |
| Delete one | `DELETE /resources/{id}` | — |
| Batch delete | `DELETE /resources` | Body: `{ids: [...]}` ([`CommonIds`](/en/develop/schema#commonids--offlinebyrolerequest)) |
| Sub-resource | `GET /resources/{id}/sub` | — |
| Derived query | `GET /resources/tree`, `GET /resources/options` | — |
| Instance action | `POST /resources/{id}/action-name` | optional body |
| Collection action | `POST /resources/batch-offline`, `POST /resources/refresh` | body |

Constraints:

- **No** trailing slashes (`/users` ✅, `/users/` ❌)
- Multi-word paths use **kebab-case** (`/batch-offline`, `/constant-routes`, `/user-routes`)
- Resource names are **plural** (`/users`, `/roles`, `/departments`)
- "Search" uniformly uses `POST /resources/search` instead of `GET ?...=...` — supports complex bodies (arrays, nesting)

## Field naming

- Request body / query: **camelCase** (Pydantic `validate_by_name=True` accepts snake_case too, but the frontend always sends camelCase)
- Response `data`: **camelCase** — use `schema.model_dump(by_alias=True)` or `model.to_dict()`

## Pagination

Body extends `PageQueryBase`:

```python
from app.utils import PageQueryBase

class DepartmentSearch(PageQueryBase):
    name: str | None = None
```

Fixed fields:

| Field | Default | Purpose |
|---|---|---|
| `current` | `1` | page (≥ 1) |
| `size` | `10` | page size (1–1000) |
| `orderBy` | `null` | sort fields, `-` prefix = desc, e.g. `["-createdAt", "id"]` |

Response:

```json
{
  "code": "0000", "msg": "OK",
  "data": {
    "records": [...],
    "total": 42,
    "current": 1,
    "size": 10
  }
}
```

## IDs are sqids

All public-facing resource IDs are **sqid strings** (e.g. `Yc7vN3kE`) — never raw auto-increment ints. Use [`SqidId`](/en/develop/sqids) in Pydantic schemas and `SqidPath` for path params:

```python
from app.utils import SqidId, SqidPath, SchemaBase

class DepartmentUpdate(SchemaBase):
    parent_id: SqidId | None = None        # body field

@router.get("/departments/{item_id}")
async def get_dept(item_id: SqidPath):     # path param
    ...
```

`SqidId` decodes the sqid to int on input and re-encodes to sqid on output. `SqidPath` decodes only. See [Sqids](/en/develop/sqids).

## CRUDRouter — don't hand-write

The default way to add a resource's routes is `CRUDRouter` — 6 standard REST routes in a single declaration:

```python
from app.utils import CRUDRouter, SearchFieldConfig, require_buttons

dept_crud = CRUDRouter(
    prefix="/departments",
    controller=department_controller,
    create_schema=DepartmentCreate,
    update_schema=DepartmentUpdate,
    list_schema=DepartmentSearch,
    search_fields=SearchFieldConfig(
        contains_fields=["name", "code"],
        exact_fields=["status"],
    ),
    summary_prefix="Department",
    soft_delete=True,
    tree_endpoint=True,
    action_dependencies={
        "create": [require_buttons("B_HR_DEPT_CREATE")],
        "update": [require_buttons("B_HR_DEPT_EDIT")],
        "delete": [require_buttons("B_HR_DEPT_DELETE")],
        "batch_delete": [require_buttons("B_HR_DEPT_DELETE")],
    },
)
router = dept_crud.router
```

To customize a route, use `@crud.override("list")` — **don't** redeclare the same path on the router; it'll be shadowed by `_OrderedRouter` reordering. Full API in [CRUDRouter](/en/develop/crud-router).

## Auth dependencies

| Dependency | Purpose |
|---|---|
| `DependAuth` | JWT validation only, no permission check (captcha, impersonate, user info) |
| `DependPermission` | On top of `DependAuth`, matches `(method, path)` against `role.apis` (default for business endpoints) |
| `require_buttons("B_X", ...)` | Any one passes; otherwise `2203` |
| `require_buttons(..., require_all=True)` | All required; otherwise `2202` |
| `require_roles("R_X", ...)` | Same as buttons but for roles; codes `2204 / 2205` |

`R_SUPER` bypasses everything. See [Auth](/en/develop/auth).

## Endpoint cheat sheet

### Auth (`/api/v1/auth`, public)

| Method | Path | Purpose |
|---|---|---|
| POST | `/login` | Username + password |
| POST | `/captcha` | Send phone captcha |
| POST | `/code-login` | Captcha login |
| POST | `/register` | Register (default role `R_USER`) |
| POST | `/refresh-token` | Refresh access token |
| GET | `/user-info` | Current user info + roles + buttons (`DependAuth`) |
| PATCH | `/password` | Change password (`DependAuth`, increments token version) |
| POST | `/impersonate/{user_id}` | Super-admin impersonate (`DependPermission` + super check) |

### Route (`/api/v1/route`)

| Method | Path | Purpose |
|---|---|---|
| GET | `/constant-routes` | Public routes (login / error pages) from Redis |
| GET | `/user-routes` | Current user's menu tree (`DependAuth`) |
| GET | `/exists?name=xxx` | Check if a route name exists (`DependAuth`) |

### System manage (`/api/v1/system-manage`, all behind `DependPermission`)

Each follows the standard 6-route convention:

| Resource | Prefix | Notes |
|---|---|---|
| Users | `/users` | `create / update` are `@override`d for password hashing + role association |
| Roles | `/roles` | Includes `GET /roles/{id}/menus`, `PATCH /roles/{id}/menus`, etc. |
| Menus | `/menus` | Includes `GET /menus/tree`, `GET /menus/pages` |
| APIs | `/apis` | **Read-only** (`list / get / tree / tags` only); records are reconciled by `refresh_api_list()` at startup |
| Dictionary | `/dictionaries` | Includes `GET /dictionaries/{type}/options` (5-min Redis cache) |

### Business modules (`/api/v1/business/<name>`)

Per-module. The complete HR module endpoint list is in [HR module](/en/develop/business-hr).

## Response wrappers

| Class | Purpose | Typical scenario |
|---|---|---|
| `Success(data=...)` | Single / non-paginated | get / create / update |
| `SuccessExtra(data={"records": [...]}, total, current, size)` | Paginated | list / search |
| `Fail(code=Code.X, msg="...")` | Business failure | rule violation |
| `Custom(code, status_code, msg, data, **kwargs)` | Anything | rare custom status_code |

::: tip OpenAPI response model
`Success` etc. are `JSONResponse` subclasses; FastAPI cannot infer the response shape. To document accurately, add `response_model=ResponseModel[UserOut]` or `PageResponseModel[UserOut]`. See [Schema base](/en/develop/schema#openapi-response-models).
:::

## Static-path priority inside the router

`CRUDRouter` uses `_OrderedRouter`: every `add_api_route` triggers a re-sort that moves paths without `{...}` to the front. This prevents `GET /resources/{id}` from shadowing later-added `GET /resources/tree`. **Don't** bypass this (e.g. by mutating `router.routes.append(...)`).
