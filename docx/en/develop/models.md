# Data Models (System)

System models live in `app/system/models/admin.py` and `app/system/models/dictionary.py`. All inherit `BaseModel + AuditMixin`; primary keys and foreign keys are auto-encoded as [sqid](/en/develop/sqids) at the HTTP boundary.

> Business module models live in `app/business/<name>/models.py`. See [Mixins](/en/develop/mixins) and [HR module](/en/develop/business-hr) for conventions.

## User

Table: `users`

| Field | Type | Notes |
|---|---|---|
| `id` | int PK | — |
| `user_name` | str(20) unique | login name |
| `password` | str(128) | Argon2 hash |
| `nick_name` | str(30) null | display name |
| `user_gender` | enum(`GenderType`) | `male / female / unknow` |
| `user_email` | str(255) unique null | email |
| `user_phone` | str(20) null | phone |
| `last_login` | datetime null | last login time |
| `status_type` | enum(`StatusType`) | `enable / disable / invalid` |
| `token_version` | int default=0 | paired with Redis `token_version:{uid}` for session invalidation |
| `must_change_password` | bool default=False | force change at first login |
| `created_at / updated_at` | datetime | maintained by `AuditMixin` |
| `created_by / updated_by` | str(64) null | `CRUDBase` writes from `CTX_USER_ID` |

Relations:

- `by_user_roles` — M2M → Role

> `token_version` is the JWT invalidation primitive: `INCR` once after password change / forced logout / impersonation exit and all old tokens fail. See [Auth](/en/develop/auth#token-invalidation-token_version).

## Role

Table: `roles`

| Field | Type | Notes |
|---|---|---|
| `id` | int PK | — |
| `role_name` | str(20) unique | role name |
| `role_code` | str(20) unique | role code (e.g. `R_HR_ADMIN`) |
| `role_desc` | str(500) null | description |
| `data_scope` | enum(`DataScopeType`) default=`all` | row-level scope (see [data scope](/en/develop/data-scope)) |
| `by_role_home` | FK → Menu | default landing menu |
| `status_type` | enum(`StatusType`) | status |

Relations:

- `by_role_menus` — M2M → Menu
- `by_role_apis` — M2M → Api
- `by_role_buttons` — M2M → Button
- `by_role_users` — Reverse → User

::: warning data_scope default = `all` is a pitfall
The model defaults `data_scope` to `all`, so omitting it in `ensure_role(...)` makes the role "see everything". **Always set it explicitly** in business seeds or department managers will see the entire company.
:::

## Menu

Table: `menus`

| Field | Type | Notes |
|---|---|---|
| `id` | int PK | — |
| `menu_name` | str(100) | menu label |
| `menu_type` | enum(`MenuType`) | `catalog` / `menu` |
| `route_name` | str(100) unique | router `name` |
| `route_path` | str(200) unique | router path |
| `path_param` | str(200) null | path params |
| `route_param` | JSON null | route params (list[dict]) |
| `order` | int default=0 | sibling order |
| `component` | str(100) null | `view.xxx` / `layout.base$view.xxx` |
| `parent_id` | int default=0 | parent menu (0 = top) |
| `i18n_key` | str(100) null | i18n key (overrides `menu_name`) |
| `icon` | str(100) null | icon name |
| `icon_type` | enum(`IconType`) | `iconify` / `local` |
| `href` | str(200) null | external link |
| `multi_tab` | bool | allow multiple tabs for same route |
| `keep_alive` | bool | cache page state |
| `hide_in_menu` | bool | hidden (e.g. detail pages) |
| `active_menu` | FK self null | "highlight parent" for hidden routes |
| `fixed_index_in_tab` | int null | pinned tab index |
| `status_type` | enum | status |
| `redirect` | str(200) null | redirect path |
| `props` | bool | root route flag |
| `constant` | bool | public route (login etc.) |

Relations:

- `by_menu_buttons` — M2M → Button
- `by_menu_roles` — Reverse → Role

## Api

Table: `apis`

| Field | Type | Notes |
|---|---|---|
| `id` | int PK | — |
| `api_path` | str(500) | path (with `{item_id}` placeholders) |
| `api_method` | enum(`MethodType`) | `get / post / put / patch / delete` |
| `summary` | str(500) null | endpoint summary |
| `tags` | JSON | tags |
| `status_type` | enum | `enable` allows; `disable` rejects with `2200` |
| `is_system` | bool default=False | auto-registered marker |

`refresh_api_list()` reconciles the FastAPI route table with the `Api` table on every startup:

- routes ↔ table set diff
- extra → DELETE + Radar `WARNING "API deleted"`
- missing → INSERT
- existing → UPDATE summary / tags

Developers **never** maintain the `Api` table by hand. See [RBAC / API auto-reconcile](/en/develop/rbac#api-auto-reconcile).

## Button

Table: `buttons`

| Field | Type | Notes |
|---|---|---|
| `id` | int PK | — |
| `button_code` | str(200) indexed | code (e.g. `B_HR_EMP_CREATE`) |
| `button_desc` | str(200) | description |
| `status_type` | enum | status |

Relations:

- `by_button_menus` — Reverse → Menu (button mounted on menu)
- `by_button_roles` — Reverse → Role

Naming convention: `B_<MODULE>_<RESOURCE>_<ACTION>`. See [RBAC / button naming](/en/develop/rbac#button-naming-convention).

## Dictionary (system dictionary)

Table: `sys_dictionary`, unique constraint `(dict_type, value)`.

| Field | Type | Notes |
|---|---|---|
| `id` | int PK | — |
| `dict_type` | str(100) | type (e.g. `tag_category` / `employee_position`) |
| `label` | str(100) | label |
| `value` | str(100) | stored value |
| `order` | int default=0 | sort |
| `status` | enum | status |
| `remark` | str(500) null | note |

Purpose: turn "dropdown options" into back-office-configurable resources. Frontend hits `GET /api/v1/system-manage/dictionaries/{dict_type}/options` (5-min Redis cache).

Seed example (HR's `Tag.category` references `dict_type="tag_category"`):

```python
DICTIONARY_SEEDS = [
    {"dict_type": "tag_category", "label": "Working style", "value": "working_style", "order": 1},
    ...
]
```

## Database

- Default: SQLite (`app_system.sqlite3`)
- Switch to PostgreSQL / MySQL / SQL Server via `.env` `DB_URL` (**no code change**), see [Switching DB](/en/ops/database)
- Business modules can declare a standalone `DB_URL`; autodiscover registers a separate Tortoise connection

## Migrations

Tables are **not** auto-created at startup. After model changes:

```bash
make mm     # = tortoise makemigrations + migrate
```

Migrations live in `migrations/<app_name>/` (system + shared business in `migrations/app_system/`; standalone-DB modules in `migrations/app_<biz>/`).

## See also

- [Mixins](/en/develop/mixins) — `BaseModel / AuditMixin / TreeMixin / SoftDeleteMixin`
- [Sqids](/en/develop/sqids) — how PK / FK become sqid strings
- [RBAC](/en/develop/rbac) — User / Role / Menu / Button / API together
- [HR module](/en/develop/business-hr) — business module model sample
