# CRUDRouter

A factory that mass-generates the 6 standard REST routes; pair with [`CRUDBase`](/en/develop/crud) and [API conventions](/en/develop/api). Kills 90% of boilerplate.

Source: `app/core/router.py`.

## Generated routes

| Name | Method + path | Enabled when | Body / Param |
|---|---|---|---|
| `list` | `POST /{prefix}/search` | `list_schema` provided | `list_schema` (with `current/size/orderBy`) |
| `get` | `GET /{prefix}/{item_id}` | always | `item_id: SqidPath` |
| `create` | `POST /{prefix}` | `create_schema` provided | `create_schema` |
| `update` | `PATCH /{prefix}/{item_id}` | `update_schema` provided | `item_id` + `update_schema` |
| `delete` | `DELETE /{prefix}/{item_id}` | always | `item_id` |
| `batch_delete` | `DELETE /{prefix}` | always | `CommonIds` (`{ids: [...]}`) |

`tree_endpoint=True` adds `GET /{prefix}/tree`.

## Minimal example

```python
from app.utils import CRUDBase, CRUDRouter, SearchFieldConfig

tag_controller = CRUDBase(model=Tag)

tag_crud = CRUDRouter(
    prefix="/tags",
    controller=tag_controller,
    create_schema=TagCreate,
    update_schema=TagUpdate,
    list_schema=TagSearch,
    search_fields=SearchFieldConfig(
        contains_fields=["name"],
        exact_fields=["category"],
    ),
    summary_prefix="Tag",
)
router = tag_crud.router
```

`prefix` must start with a slash (`/tags`); the last segment becomes the resource name in the generated paths.

## Full parameters

```python
CRUDRouter(
    prefix: str,
    controller: CRUDBase,
    create_schema: type[BaseModel] | None = None,
    update_schema: type[BaseModel] | None = None,
    list_schema: type[BaseModel] | None = None,
    search_fields: SearchFieldConfig | None = None,
    summary_prefix: str = "",
    list_order: list[str] | None = None,           # default ["id"]
    exclude_fields: list[str] | None = None,       # to_dict exclusion
    enable_routes: set[str] | None = None,         # default all
    record_transform: Callable | None = None,      # async def transform(obj) -> dict
    soft_delete: bool = False,                     # use controller.soft_remove
    tree_endpoint: bool = False,                   # register GET /tree
    action_dependencies: dict[str, Sequence] | None = None,
)
```

### `search_fields: SearchFieldConfig`

```python
SearchFieldConfig(
    contains_fields=[...],     # __contains
    icontains_fields=[...],    # __icontains
    exact_fields=[...],        # equal
    iexact_fields=[...],       # __iexact
    in_fields=[...],           # __in
    range_fields=[...],        # expects {field}_start / {field}_end on the schema
)
```

See [`build_search`](/en/develop/crud#build_search--auto-build-q-from-a-schema).

### `enable_routes` — disable some routes

```python
crud = CRUDRouter(..., enable_routes={"list", "get"})  # read-only
```

### `record_transform` — custom return shape

Default: `await obj.to_dict(exclude_fields=...)`. To preload relations or compose fields:

```python
async def transform(obj: Employee) -> dict:
    d = await obj.to_dict()
    await obj.fetch_related("department")
    d["departmentName"] = obj.department.name
    return d

CRUDRouter(..., record_transform=transform)
```

> Recommended only for small field-composition cases. For N+1 optimization (`select_related` / `prefetch_related`) use `@override("list")` directly.

### `soft_delete` — soft delete

Requires the model to inherit `SoftDeleteMixin`.

```python
CRUDRouter(..., soft_delete=True)
# delete       → controller.soft_remove
# batch_delete → controller.soft_batch_remove
```

### `tree_endpoint` — tree

Requires the model to have `parent_id` (recommended via `TreeMixin`). The generated `GET /resources/tree` uses `_build_nested_tree(records, parent_id_key="parentId", root_value=0)`.

### `action_dependencies` — per-route dependencies

```python
CRUDRouter(
    ...,
    action_dependencies={
        "create":       [require_buttons("B_HR_DEPT_CREATE")],
        "update":       [require_buttons("B_HR_DEPT_EDIT")],
        "delete":       [require_buttons("B_HR_DEPT_DELETE")],
        "batch_delete": [require_buttons("B_HR_DEPT_DELETE")],
    },
)
```

**Critical**: `action_dependencies` apply to `@override("create")`-replaced routes too — customization can't accidentally drop the permission check.

## Customize a route: `@crud.override`

To customize, **don't** redeclare `@router.post("/users")` — `_OrderedRouter`'s sort will hit the default route. Use:

```python
@user_crud.override("create")
async def _create_user(user_in: UserCreate, request: Request):
    ...
    return Success(...)
```

`override` does three things:

1. Removes the default route (matched by path + methods)
2. Registers your function on the same path / methods / summary
3. Auto-mounts `action_dependencies[name]`

Standard signatures (or call `crud.get_route_info("create")`):

```text
list:         async def list_items(obj_in: <list_schema>)
get:          async def get_item(item_id: SqidPath)
create:       async def create_item(obj_in: <create_schema>)
update:       async def update_item(item_id: SqidPath, obj_in: <update_schema>)
delete:       async def delete_item(item_id: SqidPath)
batch_delete: async def batch_delete(obj_in: CommonIds)
```

Parameters can be **freely extended** (FastAPI dependency semantics):

```python
@user_crud.override("update")
async def _update(item_id: SqidPath, obj_in: UserUpdate, request: Request):
    redis = request.app.state.redis
    ...
```

::: warning Omit a schema and the route isn't generated
If `emp_crud` doesn't pass `create_schema`, no `POST /employees` is registered. That's intentional — it lets you hand-write `@router.post("/employees")` without conflict. HR's employee create uses this pattern.
:::

## Mount extra endpoints on the router

`crud.router` is a regular `APIRouter`; mount anything beyond the standard 6:

```python
router = dept_crud.router

@router.post("/departments/{dept_id}/employees", summary="Bulk assign employees")
async def assign_employees(dept_id: SqidPath, body: AssignEmployees):
    ...
    return Success(...)
```

## Wiring template for a business module

```python
# app/business/hr/api/manage.py
from fastapi import APIRouter

from app.utils import CRUDRouter, DependPermission, SearchFieldConfig, require_buttons

dept_crud = CRUDRouter(
    prefix="/departments",
    controller=department_controller,
    create_schema=DepartmentCreate,
    update_schema=DepartmentUpdate,
    list_schema=DepartmentSearch,
    search_fields=SearchFieldConfig(contains_fields=["name", "code"]),
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

# Top router: module prefix + default deps here
router = APIRouter(prefix="/hr", tags=["hr"], dependencies=[DependPermission])
router.include_router(dept_crud.router)

# api/__init__.py aggregates manage / dept / my sub-routers into the top router
```

The module's `api/__init__.py` must export `router: APIRouter` for autodiscover to mount it under `/api/v1/business/`.

## Static-path priority

`CRUDRouter.router` is an `_OrderedRouter` — every `add_api_route` re-sorts so non-`{...}` paths come first. This guarantees later-mounted `GET /resources/pages` isn't shadowed by an earlier `GET /resources/{item_id}`.

> If you `router.routes.append(...)` directly, the sort doesn't run — don't.

## See also

- [CRUDBase](/en/develop/crud)
- [API conventions](/en/develop/api)
- [Schema base](/en/develop/schema)
- [Auth](/en/develop/auth) — `require_buttons` / `require_roles`
