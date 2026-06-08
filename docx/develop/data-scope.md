# 数据权限（data_scope）

RBAC 控制"哪些菜单/接口/按钮能用"，data_scope 控制"看到哪些行"——例如租户管理员只看本租户客户、项目负责人只看本项目订单、普通用户只看自己的资料。

源码：[`app/core/data_scope.py`](../../../app/core/data_scope.py)。

## 四种范围

| 值 | 含义 | 典型角色 |
|---|---|---|
| `all` | 全部数据，不过滤 | HR 总管 / 系统管理员 |
| `scope` | 当前业务范围数据 | 租户管理员 / 组织主管 / 项目负责人 |
| `self` | 仅本人数据 | 普通员工 |
| `custom` | 预留，当前降级到 `self` | — |

`R_SUPER` 与 `data_scope=all` 都不会附加任何过滤条件。

## 多角色取最宽松

一个用户可以同时持多个角色（例如平台管理员 + 租户管理员）。计算最终 scope 时取**最宽松**的：

```
all  >  scope  >  self  >  custom
```

实际计算见 `get_current_data_scope(redis)`：遍历 `CTX_ROLE_CODES`，逐个读 `role:{code}:data_scope`，取优先级最高（数字最小）的。

## 角色种子必须显式声明

`Role` 模型默认 `data_scope=all`，因此 `ensure_role()` 不传该参数时角色就是"全可见"。**业务角色一律显式声明**：

```python
BIZ_ROLE_SEEDS = [
    {
        "role_code": "R_PLATFORM_ADMIN",
        "data_scope": DataScopeType.all,             # 显式 all
        ...
    },
    {
        "role_code": "R_TENANT_ADMIN",
        "data_scope": DataScopeType.scope,           # 当前业务范围
        ...
    },
    {
        "role_code": "R_USER",
        "data_scope": DataScopeType.self_,           # 注意 Python 关键字 → self_
        ...
    },
]
```

> 这条规则在 [`ensure_role`](../../../app/system/services/init_helper.py) 里没有强制（不传就维持原值）——靠 code review。漏写的话业务范围角色会变成"全量可见"。

## 业务接口怎么用

```python
from app.business.crm.ctx import get_current_scope_id
from app.business.crm.services import build_customer_list_query, list_customers_with_relations
from app.core.data_scope import get_current_data_scope
from app.utils import CTX_USER_ID, SuccessExtra, build_scope_filter

@customer_crud.override("list")
async def _list_customers(obj_in: CustomerSearch, request: Request):
    q = build_customer_list_query(obj_in)
    scope = await get_current_data_scope(request.app.state.redis)
    scope_q = build_scope_filter(
        scope=scope,
        user_id=CTX_USER_ID.get(),
        scope_id=get_current_scope_id(),       # 业务模块自带的 ContextVar 工具
        user_id_field="owner_id",              # 模型中用户字段名
        scope_id_field="tenant_id",            # 模型中业务范围字段名
    )
    total, records = await list_customers_with_relations(obj_in, search=q & scope_q)
    return SuccessExtra(data={"records": records}, total=total, current=obj_in.current, size=obj_in.size)
```

`build_scope_filter`：

| 入参 | scope 命中 → 行为 |
|---|---|
| `is_super_admin()` 或 `scope == "all"` | 返回空 `Q()`，不过滤 |
| `scope == "scope"` 且 `scope_id` 不为空 | `Q(<scope_id_field>=...)` |
| 其他（含 `self` / `custom`） | `Q(user_id=...)` |

字段名通过 `user_id_field` / `scope_id_field` 参数指定，不强制为 `user_id` / `scope_id`。

## 模块怎么提供 scope_id

业务模块通常用一个本模块的 ContextVar + 依赖来注入"当前用户的业务范围 ID"。这个范围可以是租户、组织、项目、门店等，不再要求系统存在固定部门字段：

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
# app/business/crm/dependency.py — 在 router 上挂的依赖
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

这样所有 CRM 路由进入 service 时 `get_current_scope_id()` 都能拿到正确值。

## Redis 失败时降级

`get_current_data_scope(redis=None)` 会回退到 DB 查询（`Role.filter(role_code__in=...)`）。生产环境 Redis 故障时数据范围依然生效，只是性能下降。

## 哪些资源应当受 scope 限制

不需要给所有表都加 scope。判断标准：

- **强 scope**：订单、客户、工单等"含个人或业务范围归属"的业务表
- **不需要**：字典、菜单、角色、按钮等系统配置类（用 RBAC 即可）
- **慎用**：日志类（按 `actor_id` 限制可能让管理员看不到完整审计链）

## 与 `CRUDRouter` 的关系

`CRUDRouter` 默认的 `list` 路由不加 scope（它不知道你的字段叫什么）。涉及行级权限的资源请 `@override("list")`：

```python
@emp_crud.override("list")
async def _list(obj_in: EmployeeSearch, request: Request):
    q = build_employee_list_query(obj_in)
    scope = await get_current_data_scope(request.app.state.redis)
    q &= build_scope_filter(
        scope=scope,
        user_id=CTX_USER_ID.get(),
        scope_id=get_current_department_id(),
        user_id_field="user_id",
        scope_id_field="department_id",
    )
    total, records = await list_employees_with_relations(obj_in, search=q)
    return SuccessExtra(data={"records": records}, total=total, current=obj_in.current, size=obj_in.size)
```

CLI 可以直接生成这个 override：

```bash
uv run python -m app.cli crud crm --models Customer --data-scope Customer:owner_id,tenant_id
```

生成代码会把 `user_id_field` / `scope_id_field` 写入 `build_scope_filter()`，并生成 `_get_scope_id()` 钩子。范围级权限需要在本模块里把该钩子接到业务上下文；未接入时 `scope` 档位会按 `build_scope_filter()` 的规则降级到 `self`。

## 与接口级权限的关系

`data_scope` 管的是"同一接口下能看到哪些行"；接口本身"能不能调"由 `DependPermission` 按 `(method, APIRoute.path_format)` 精确判定。两层互补、独立：

- `DependPermission` 的键是 FastAPI 匹配到的路由模板——`/resources/{id}` 和 `/resources/sync` 是两条完全独立的权限记录，不会互相蹭权限。详见 [RBAC / 匹配语义](./rbac.md#匹配语义按-path_format-精确命中)。
- 在 `@crud.override("list")` 里拼 `build_scope_filter(...)` 时不需要再检查调用者是否有该接口的权限——`DependPermission` 已经在进入 handler 前挡住未授权访问。

## 相关

- [RBAC 模型](./rbac.md)
- [HR 模块（行级权限完整实例）](../advanced/business-hr.md)
- [缓存](../ops/cache.md) — `role:{code}:data_scope`
