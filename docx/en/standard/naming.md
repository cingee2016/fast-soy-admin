# Naming Conventions

## Files / directories

| Side | Convention | Example |
|---|---|---|
| Frontend file / dir | `kebab-case` | `user-list.vue`, `hooks/use-table.ts` |
| Backend file / dir | `snake_case` | `init_helper.py`, `inventory/api/manage.py` |
| Business module name | `snake_case`, single word | `inventory` / `inventory` / `notify` |

## Python identifiers

| Kind | Convention | Example |
|---|---|---|
| Class | `PascalCase` | `UserController` / `ProductCreate` |
| Function / method | `snake_case` | `get_user()` / `create_product()` |
| Module-level constant | `UPPER_SNAKE_CASE` | `SECRET_KEY` / `SUPER_ADMIN_ROLE` |
| Module-level private | `_snake_case` | `_safe_update_or_create()` |
| Field (DB / Schema internal) | `snake_case` | `user_name` / `created_at` |
| Field (HTTP boundary) | **camelCase** (auto-converted) | `userName` / `createdAt` |
| Pydantic schema | `PascalCase` + `Create / Update / Search / Out` suffix | `ProductCreate` / `ProductSearch` |
| Tortoise model | `PascalCase` singular | `Product` / `Warehouse` |
| Tortoise `Meta.table` | `<scope>_<module>_<entity>` | `biz_inventory_product` / `sys_dictionary` |

## TypeScript identifiers

| Kind | Convention | Example |
|---|---|---|
| Component | `PascalCase` | `UserCard` |
| Composable / hook | `useXxx` | `useTable` / `useAuth` |
| Function | `camelCase` | `getUser()` |
| Constant | `UPPER_SNAKE_CASE` | `MAX_COUNT` |
| API request function | `fetchXxx` | `fetchUserList()` / `fetchLogin()` |
| Type / interface | `Api.<Module>.<Type>` | `Api.User.UserOut` |

## URL / path

| Kind | Convention | Example |
|---|---|---|
| Resource segment | plural + `kebab-case` | `/users` / `/warehouses` / `/system-manage/users` |
| Sub-resource | plural + parent ID | `/roles/{id}/menus` |
| Collection action | resource + `/<verb-noun>` | `/roles/batch-offline` / `/apis/refresh` |
| Instance action | `/{id}/<verb-noun>` | `/products/{id}/transition` |
| Derived query | `/<noun>` | `/menus/tree` / `/menus/pages` |
| **Avoid** | trailing slash, camelCase, mixing plural & singular | ❌ `/users/` / ❌ `/userList` / ❌ `/user` |

## Business codes

```
B_<MODULE>_<RESOURCE>_<ACTION>  # Button code
R_<UPPER>                       # Role code
```

| Example | Meaning |
|---|---|
| `B_INVENTORY_PRODUCT_CREATE` | Inventory / product / create |
| `B_INVENTORY_PRODUCT_TRANSITION` | Inventory / product / state transition |
| `R_INVENTORY_ADMIN` | inventory admin |
| `R_DEPT_MGR` | generic warehouse manager |
| `R_SUPER` | super admin (reserved) |

## Route name (menu route_name)

```
<module>               # top-level catalog
<module>_<page>        # second-level page
<module>_<page>_<sub>  # third level
```

| Example | Path |
|---|---|
| `home` | `/home` |
| `inventory` | `/inventory` |
| `inventory_warehouse` | `/inventory/warehouse` |
| `inventory_product_detail` | `/inventory/product/detail` |
| `function_multi-tab` | `/function/multi-tab` (kebab inside a segment) |

`route_name` is the Vue Router `name` and the unique key on `Menu.route_name` — **keep it stable**. Renaming means every role seed referencing it must be updated too.

## i18n key

```
route.<route_name>   # route / menu title
page.<module>.<key>  # in-page text
common.<key>         # global
```

## Cache key

| Scope | Template | Example |
|---|---|---|
| System-level permission | `role:{code}:*` / `user:{uid}:*` | `role:R_INVENTORY_ADMIN:apis` |
| Business module | `<module>_<resource>:<scope>` | `dict_options:tag_category` |
| Startup coordination | `app:<purpose>` | `app:init_lock` / `app:init_done` |

## Event name

```
<aggregate>.<verb>  # lowercase + dot
```

| Example | Meaning |
|---|---|
| `product.created` | product created |
| `product.status_changed` | product state transition |
| `order.refunded` | order refunded |

## Database

| Kind | Convention |
|---|---|
| Table name | `<scope>_<module>_<entity>` (lowercase + underscore, singular) |
| PK | `id` (int) |
| FK field | `<entity>_id` (e.g. `team_id`) |
| Time fields | `created_at` / `updated_at` / `deleted_at` |
| Status field | `status` or `status_type` (matching frontend expectation) |

## Other

- Module-level `__all__` exposes only the truly public symbols; keep private with `_` prefix
- Test files are named after the module under test with `test_` prefix (`tests/test_product_service.py`)
- Avoid single-letter variable names (`l, O, I` collide in some fonts); loop counters `i, j` are OK
