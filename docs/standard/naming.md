# 命名规范

## 文件 / 目录

| 端 | 规范 | 示例 |
|---|---|---|
| 前端文件 / 目录 | `kebab-case` | `user-list.vue`、`hooks/use-table.ts` |
| 后端文件 / 目录 | `snake_case` | `init_helper.py`、`inventory/api/manage.py` |
| 业务模块名 | `snake_case`，单词 | `inventory` / `inventory` / `notify` |

## Python 标识符

| 类型 | 规范 | 示例 |
|---|---|---|
| 类 | `PascalCase` | `UserController` / `ProductCreate` |
| 函数 / 方法 | `snake_case` | `get_user()` / `create_product()` |
| 模块级常量 | `UPPER_SNAKE_CASE` | `SECRET_KEY` / `SUPER_ADMIN_ROLE` |
| 模块级私有 | `_snake_case` | `_safe_update_or_create()` |
| 字段（DB / Schema 内部） | `snake_case` | `user_name` / `created_at` |
| 字段（HTTP 边界） | **camelCase**（自动转换） | `userName` / `createdAt` |
| Pydantic 模型 | `PascalCase` + `Create / Update / Search / Out` 后缀 | `ProductCreate` / `ProductSearch` |
| Tortoise 模型 | `PascalCase` 单数 | `Product` / `Warehouse` |
| Tortoise `Meta.table` | `<scope>_<module>_<entity>` | `biz_inventory_product` / `sys_dictionary` |

## TypeScript 标识符

| 类型 | 规范 | 示例 |
|---|---|---|
| 组件名 | `PascalCase` | `UserCard` |
| Composable / hook | `useXxx` | `useTable` / `useAuth` |
| 函数 | `camelCase` | `getUser()` |
| 常量 | `UPPER_SNAKE_CASE` | `MAX_COUNT` |
| API 请求函数 | `fetchXxx` | `fetchUserList()` / `fetchLogin()` |
| 类型 / 接口 | `Api.<Module>.<Type>` | `Api.User.UserOut` |

## URL / 路径

| 类型 | 规范 | 示例 |
|---|---|---|
| 资源段 | 复数 + `kebab-case` | `/users` / `/warehouses` / `/system-manage/users` |
| 子资源 | 复数 + 父 ID | `/roles/{id}/menus` |
| 集合动作 | 资源 + `/<verb-noun>` | `/roles/batch-offline` / `/apis/refresh` |
| 实例动作 | `/{id}/<verb-noun>` | `/products/{id}/transition` |
| 派生查询 | `/<noun>` | `/menus/tree` / `/menus/pages` |
| **不要** | 尾斜杠、camelCase、复数 + 单数混用 | ❌ `/users/` / ❌ `/userList` / ❌ `/user` |

## 业务码

```
B_<MODULE>_<RESOURCE>_<ACTION>  # 按钮编码
R_<UPPER>                       # 角色编码
```

| 例 | 含义 |
|---|---|
| `B_INVENTORY_PRODUCT_CREATE` | 库存 / 商品 / 创建 |
| `B_INVENTORY_PRODUCT_TRANSITION` | 库存 / 商品 / 状态流转 |
| `R_INVENTORY_ADMIN` | 库存管理员 |
| `R_DEPT_MGR` | 通用仓库主管 |
| `R_SUPER` | 超级管理员（保留） |

## 路由名（菜单 route_name）

```
<module>               # 顶级目录
<module>_<page>        # 二级页面
<module>_<page>_<sub>  # 三级
```

| 例 | 路径 |
|---|---|
| `home` | `/home` |
| `inventory` | `/inventory` |
| `inventory_warehouse` | `/inventory/warehouse` |
| `inventory_product_detail` | `/inventory/product/detail` |
| `function_multi-tab` | `/function/multi-tab`（多词在段内用 kebab） |

`route_name` 是前端 vue-router 的 `name`，也是后端 `Menu.route_name` 唯一键，**务必稳定**——改名意味着所有引用它的角色 seed 都要改。

## i18n key

```
route.<route_name>   # 路由 / 菜单标题
page.<module>.<key>  # 页面内文案
common.<key>         # 全局通用
```

## 缓存键

| 范围 | 模板 | 示例 |
|---|---|---|
| 系统级权限 | `role:{code}:*` / `user:{uid}:*` | `role:R_INVENTORY_ADMIN:apis` |
| 业务模块自有 | `<module>_<resource>:<scope>` | `dict_options:tag_category` |
| 启动协调 | `app:<purpose>` | `app:init_lock` / `app:init_done` |

## 事件名

```
<aggregate>.<verb>  # 小写 + 点
```

| 例 | 含义 |
|---|---|
| `product.created` | 商品创建 |
| `product.status_changed` | 商品状态流转 |
| `order.refunded` | 订单退款 |

## 数据库

| 类型 | 规范 |
|---|---|
| 表名 | `<scope>_<module>_<entity>`（小写 + 下划线，单数） |
| 主键 | `id`（int） |
| 外键字段 | `<entity>_id`（如 `team_id`） |
| 时间字段 | `created_at` / `updated_at` / `deleted_at` |
| 状态字段 | `status` 或 `status_type`（按前端期望） |

## 其他

- Python 模块的 `__all__` 仅暴露真正的"公开符号"，私有用 `_` 前缀
- 测试文件与被测模块同名 + `test_` 前缀（`tests/test_product_service.py`）
- 不要用单字母变量名（`l, O, I` 在某些字体下会混淆）；循环计数允许 `i, j`
