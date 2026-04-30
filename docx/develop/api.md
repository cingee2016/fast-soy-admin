# API 约定

所有 system / business 接口共用同一套强制约定，偏离请先讨论。

完整 API 参考：[Apidog](https://fast-soy-admin.apidog.io)。本文聚焦**约定**与**关键端点速查**。

## 路由前缀

| 前缀 | 用途 |
|---|---|
| `/api/v1/auth` | 认证（公开） |
| `/api/v1/route` | 路由（前端拉常量路由 / 用户路由） |
| `/api/v1/system-manage/*` | 系统模块（用户 / 角色 / 菜单 / API / 字典） |
| `/api/v1/business/<module>/*` | 业务模块（autodiscover 自动挂载） |

## 响应格式

任何成功响应一律：

```json
{ "code": "0000", "msg": "OK", "data": { ... } }
```

字段命名一律 **camelCase**——`SchemaBase` 的 `alias_generator=to_camel_case` 自动处理；`Model.to_dict()` 同样输出 camelCase。**禁止**返回裸 dict，**禁止**手工拼 snake_case。

详细的码段 / 前端映射见 [响应码](../reference/codes.md)。

## 路径与方法约定

| 操作 | 方法 + 路径 | Body / Params |
|---|---|---|
| 列表 / 搜索 | `POST /resources/search` | Body 继承 `PageQueryBase` |
| 单条查询 | `GET /resources/{id}` | — |
| 创建 | `POST /resources` | Body: `XxxCreate` |
| 更新 | `PATCH /resources/{id}` | Body: `XxxUpdate` |
| 单条删除 | `DELETE /resources/{id}` | — |
| 批量删除 | `DELETE /resources` | Body: `{ids: [...]}`（[`CommonIds`](./schema.md#commonids--offlinebyrolerequest)） |
| 子资源查询 | `GET /resources/{id}/sub` | — |
| 派生查询 | `GET /resources/tree`、`GET /resources/options` | — |
| 实例动作 | `POST /resources/{id}/action-name` | 视情况带 Body |
| 集合动作 | `POST /resources/batch-offline`、`POST /resources/refresh` | Body |

约束：

- **不要**带尾斜杠（`/users` ✅ ，`/users/` ❌）
- 多词路径用 **kebab-case**（`/batch-offline`、`/constant-routes`、`/user-routes`）
- 资源名一律 **复数**（`/users`、`/roles`、`/departments`）
- "搜索"统一用 `POST /resources/search` 而不是 `GET ?...=...`——支持复杂查询体（数组、嵌套）

## 字段命名

- 请求 body / query 一律 **camelCase**（Pydantic `validate_by_name=True` 兼容 snake_case，但前端始终发 camelCase）
- 响应 `data` 一律 **camelCase**——使用 `schema.model_dump(by_alias=True)` 或 `model.to_dict()`

## 分页约定

请求体继承 `PageQueryBase`：

```python
from app.utils import PageQueryBase

class DepartmentSearch(PageQueryBase):
    name: str | None = None
```

固定字段：

| 字段 | 默认 | 说明 |
|---|---|---|
| `current` | `1` | 页码（≥ 1） |
| `size` | `10` | 每页数量（1–1000） |
| `orderBy` | `null` | 排序字段列表，`-` 前缀降序，例 `["-createdAt", "id"]` |

响应体：

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

## ID 一律 sqid

所有对外暴露的资源 ID 是 **sqid 字符串**（如 `Yc7vN3kE`），不是自增 int。Pydantic schema 中用 [`SqidId`](./sqids.md)，路径参数用 `SqidPath`：

```python
from app.utils import SqidId, SqidPath, SchemaBase

class DepartmentUpdate(SchemaBase):
    parent_id: SqidId | None = None        # body 字段

@router.get("/departments/{item_id}")
async def get_dept(item_id: SqidPath):     # 路径参数
    ...
```

`SqidId` 在校验时把 sqid 解码成 int，序列化时再编码回 sqid。`SqidPath` 只解码不参与序列化输出。详见 [Sqids 资源 ID](./sqids.md)。

## CRUDRouter — 不要手写样板路由

新增资源路由的**默认方式**是 `CRUDRouter`，6 条标准 REST 一行声明：

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
    summary_prefix="部门",
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

需要自定义某条路由时用 `@crud.override("list")`，**不要**在 router 上重新声明同路径——会被 `_OrderedRouter` 排序后遮蔽。完整 API 见 [CRUDRouter](./crud-router.md)。

## 鉴权依赖

| 依赖 | 用途 |
|---|---|
| `DependAuth` | 仅校验 JWT 与用户存在，不做权限检查（验证码、模拟登录、用户信息接口用） |
| `DependPermission` | 在 `DependAuth` 之上，按 `(method, path)` 比对 `role.apis`（业务接口默认挂在 router 上） |
| `require_buttons("B_X", ...)` | 任一通过即可，缺失返回 `2203` |
| `require_buttons(..., require_all=True)` | 全部通过，缺失返回 `2202` |
| `require_roles("R_X", ...)` | 同上，针对角色，码 `2204 / 2205` |

`R_SUPER` 自动跳过所有权限校验。详见 [认证与权限](./auth.md)。

## 关键端点速查

### 认证（`/api/v1/auth`，公开）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/login` | 用户名密码登录 |
| POST | `/captcha` | 发送手机验证码 |
| POST | `/code-login` | 验证码登录 |
| POST | `/register` | 注册（默认角色 `R_USER`） |
| POST | `/refresh-token` | 刷新 access token |
| GET | `/user-info` | 当前用户信息 + 角色 + 按钮（`DependAuth`） |
| PATCH | `/password` | 修改密码（`DependAuth`，会递增 token 版本） |
| POST | `/impersonate/{user_id}` | 超级管理员模拟登录（`DependPermission` + 超管校验） |

### 路由（`/api/v1/route`）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/constant-routes` | 公共路由（登录页 / 错误页等，从 Redis） |
| GET | `/user-routes` | 当前用户可见的菜单树（`DependAuth`） |
| GET | `/exists?name=xxx` | 校验路由名是否存在（`DependAuth`） |

### 系统管理（`/api/v1/system-manage`，全部 `DependPermission`）

每个资源都遵循上节标准 6 路由：

| 资源 | 前缀 | 备注 |
|---|---|---|
| 用户 | `/users` | `create / update` 走 `@override` 注入密码哈希 + 角色关联 |
| 角色 | `/roles` | 含 `GET /roles/{id}/menus`、`PATCH /roles/{id}/menus` 等子资源 |
| 菜单 | `/menus` | 含 `GET /menus/tree`、`GET /menus/pages` |
| API | `/apis` | **只读**（仅 `list / get / tree / tags`），由启动时 `refresh_api_list()` 全量对账维护 |
| 字典 | `/dictionaries` | 含 `GET /dictionaries/{type}/options`（带 5 分钟 Redis 缓存） |

### 业务模块（`/api/v1/business/<name>`）

按模块自治。HR 模块的完整路由见 [HR 模块](./business-hr.md)。

## 响应封装

| 类 | 用途 | 典型场景 |
|---|---|---|
| `Success(data=...)` | 单条 / 无分页 | get / create / update |
| `SuccessExtra(data={"records": [...]}, total, current, size)` | 分页 | list / search |
| `Fail(code=Code.X, msg="...")` | 业务失败 | 规则不通过 |
| `Custom(code, status_code, msg, data, **kwargs)` | 任意 | 极少数自定义 status_code 场景 |

::: tip OpenAPI 文档模型
`Success` 等是 `JSONResponse` 子类，FastAPI 默认无法在 Swagger UI 展示真实结构。需要为 OpenAPI 生成准确响应模型时，在路由上加 `response_model=ResponseModel[UserOut]` 或 `PageResponseModel[UserOut]`。详见 [Schema 基类](./schema.md#openapi-响应模型)。
:::

## 路由内顺序：静态路径优先

`CRUDRouter` 内部使用 `_OrderedRouter`，每次 `add_api_route` 后自动把不含 `{...}` 的路径排到前面，避免 `GET /resources/{id}` 遮蔽 `GET /resources/tree`。**不要**绕过它（例如直接操作 `router.routes.append(...)`）。
