# 数据模型（System）

系统模块的核心模型在 [`app/system/models/admin.py`](../../../app/system/models/admin.py) 与 [`app/system/models/dictionary.py`](../../../app/system/models/dictionary.py)。所有模型都继承 `BaseModel + AuditMixin`，外键 / 主键在 HTTP 边界自动编码为 [sqid](./sqids.md)。

> 业务模块的模型放在 `app/business/<name>/models.py`。架构与字段约定可参考 [模型 Mixin](./mixins.md) 与 [HR 模块](./business-hr.md)。

## User（用户）

表名：`users`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | int PK | 主键 |
| `user_name` | str(20) unique | 登录名 |
| `password` | str(128) | Argon2 哈希 |
| `nick_name` | str(30) null | 昵称 |
| `user_gender` | enum(`GenderType`) | `male / female / unknow` |
| `user_email` | str(255) unique null | 邮箱 |
| `user_phone` | str(20) null | 手机号 |
| `last_login` | datetime null | 最后登录时间 |
| `status_type` | enum(`StatusType`) | `enable / disable / invalid` |
| `token_version` | int default=0 | 与 Redis `token_version:{uid}` 配合做会话失效 |
| `must_change_password` | bool default=False | 首登强制改密 |
| `created_at / updated_at` | datetime | `AuditMixin` 自动维护 |
| `created_by / updated_by` | str(64) null | `CRUDBase` 自动写入 `CTX_USER_ID` |

关系：

- `by_user_roles` — M2M → Role

> `token_version` 是 JWT 失效核心机制：修改密码、强制下线、模拟登录恢复时 `INCR` 一次即可让所有旧 token 立即失效。详见 [认证](./auth.md#token-失效token_version)。

## Role（角色）

表名：`roles`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | int PK | 主键 |
| `role_name` | str(20) unique | 角色名 |
| `role_code` | str(20) unique | 角色编码（如 `R_HR_ADMIN`） |
| `role_desc` | str(500) null | 描述 |
| `data_scope` | enum(`DataScopeType`) default=`all` | 行级数据范围（[详见](./data-scope.md)） |
| `by_role_home` | FK → Menu | 默认登录后跳转的菜单 |
| `status_type` | enum(`StatusType`) | 状态 |

关系：

- `by_role_menus` — M2M → Menu
- `by_role_apis` — M2M → Api
- `by_role_buttons` — M2M → Button
- `by_role_users` — Reverse → User

::: warning data_scope 默认 all 是个坑
模型默认 `all` 让 `ensure_role(...)` 不传该参数时角色就是"全可见"。**业务种子角色一律显式声明 `data_scope`**，否则部门主管会变成全公司可见。
:::

## Menu（菜单）

表名：`menus`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | int PK | 主键 |
| `menu_name` | str(100) | 菜单名 |
| `menu_type` | enum(`MenuType`) | `catalog`(目录) / `menu`(叶子菜单) |
| `route_name` | str(100) unique | 路由名（前端 vue-router 的 name） |
| `route_path` | str(200) unique | 路由路径 |
| `path_param` | str(200) null | 路径参数 |
| `route_param` | JSON null | 路由参数（list[dict]） |
| `order` | int default=0 | 同层排序 |
| `component` | str(100) null | 组件路径（`view.xxx` / `layout.base$view.xxx`） |
| `parent_id` | int default=0 | 父菜单 ID（0=顶级） |
| `i18n_key` | str(100) null | 国际化 key（优先于 `menu_name`） |
| `icon` | str(100) null | 图标名 |
| `icon_type` | enum(`IconType`) | `iconify`(默认) / `local` |
| `href` | str(200) null | 外链 |
| `multi_tab` | bool | 是否支持同一路由开多页签 |
| `keep_alive` | bool | 是否缓存 |
| `hide_in_menu` | bool | 在菜单中隐藏（详情页常用） |
| `active_menu` | FK self null | 隐藏路由的"高亮父菜单" |
| `fixed_index_in_tab` | int null | 固定 tab 序号 |
| `status_type` | enum | 状态 |
| `redirect` | str(200) null | 重定向路径 |
| `props` | bool | 是否为根路由 |
| `constant` | bool | 是否常量路由（公共，登录页等） |

关系：

- `by_menu_buttons` — M2M → Button
- `by_menu_roles` — Reverse → Role

## Api（接口）

表名：`apis`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | int PK | 主键 |
| `api_path` | str(500) | 路径（含 `{item_id}` 占位） |
| `api_method` | enum(`MethodType`) | `get / post / put / patch / delete` |
| `summary` | str(500) null | 接口描述（FastAPI 路由的 summary） |
| `tags` | JSON | 标签 |
| `status_type` | enum | `enable` 才允许调用，`disable` 会被 `DependPermission` 拒掉（码 `2200`） |
| `is_system` | bool default=False | 是否系统自动注册（`refresh_api_list` 标记） |

启动时 `refresh_api_list()` 全量对账：

- FastAPI 路由 ↔ Api 表 set 差集
- 多余的 → DELETE + Radar `WARNING "API已删除"`
- 缺失的 → INSERT
- 已存在 → UPDATE summary / tags

详见 [RBAC / API 自动对账](./rbac.md#api自动对账)。

## Button（按钮）

表名：`buttons`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | int PK | 主键 |
| `button_code` | str(200) indexed | 按钮编码（如 `B_HR_EMP_CREATE`） |
| `button_desc` | str(200) | 描述 |
| `status_type` | enum | 状态 |

关系：

- `by_button_menus` — Reverse → Menu（按钮挂在菜单上）
- `by_button_roles` — Reverse → Role

按钮命名约定：`B_<MODULE>_<RESOURCE>_<ACTION>`，详见 [RBAC / 按钮命名约定](./rbac.md#按钮命名约定)。

## Dictionary（系统字典）

表名：`sys_dictionary`，唯一约束 `(dict_type, value)`。

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | int PK | 主键 |
| `dict_type` | str(100) | 字典类型（如 `tag_category` / `employee_position`） |
| `label` | str(100) | 显示标签 |
| `value` | str(100) | 存储值 |
| `order` | int default=0 | 排序 |
| `status` | enum | 状态 |
| `remark` | str(500) null | 备注 |

用途：把"前端下拉框的可选项"做成可在后台动态配置的资源。前端调用 `GET /api/v1/system-manage/dictionaries/{dict_type}/options` 获取启用项列表（带 5 分钟 Redis 缓存）。

写场景示例（HR 模块的 `Tag.category` 引用 `dict_type="tag_category"`）：

```python
# 系统种子（app/system/init_data.py）
DICTIONARY_SEEDS = [
    {"dict_type": "tag_category", "label": "工作方式", "value": "working_style", "order": 1},
    ...
]
```

## 数据库

- 默认 PostgreSQL（`tortoise-orm[asyncpg]`）；SQLite（`aiosqlite`，tortoise 自带）也开箱即用
- 通过 `.env` 的 `DB_URL` 切换到 SQLite / MySQL / SQL Server（**无需改代码**），详见 [切换数据库](../ops/database.md)
- 业务模块可声明独立 `DB_URL`，自动挂到独立 Tortoise 连接

## 迁移

启动时**不会**自动建表 / 迁移。模型变更后手动：

```bash
make mm     # = tortoise makemigrations + migrate
```

迁移文件位于 `migrations/<app_name>/`（系统模型 + 共用主库的业务模型在 `migrations/app_system/`，独立库的业务模块在 `migrations/app_<biz>/`）。

## 相关

- [模型 Mixin](./mixins.md) — `BaseModel / AuditMixin / TreeMixin / SoftDeleteMixin`
- [Sqids](./sqids.md) — 主键 / 外键怎么变成 sqid
- [RBAC](./rbac.md) — 用户 / 角色 / 菜单 / 按钮 / API 怎么联动
- [HR 模块](./business-hr.md) — 业务模块的模型样例（部门 / 标签 / 员工）
