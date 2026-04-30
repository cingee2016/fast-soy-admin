# 数据权限（data_scope）

RBAC 控制"哪些菜单/接口/按钮能用"，data_scope 控制"看到哪些行"——例如部门主管只看本部门员工、普通员工只看自己的资料。

源码：[`app/core/data_scope.py`](../../../app/core/data_scope.py)。

## 四种范围

| 值 | 含义 | 典型角色 |
|---|---|---|
| `all` | 全部数据，不过滤 | HR 总管 / 系统管理员 |
| `department` | 仅本部门数据 | 部门主管 |
| `self` | 仅本人数据 | 普通员工 |
| `custom` | 预留，当前降级到 `self` | — |

`R_SUPER` 与 `data_scope=all` 都不会附加任何过滤条件。

## 多角色取最宽松

一个用户可以同时持多个角色（例如 HR 总管 + 部门主管）。计算最终 scope 时取**最宽松**的：

```
all  >  department  >  self  >  custom
```

实际计算见 `get_current_data_scope(redis)`：遍历 `CTX_ROLE_CODES`，逐个读 `role:{code}:data_scope`，取优先级最高（数字最小）的。

## 角色种子必须显式声明

`Role` 模型默认 `data_scope=all`，因此 `ensure_role()` 不传该参数时角色就是"全可见"。**业务角色一律显式声明**：

```python
HR_ROLE_SEEDS = [
    {
        "role_code": "R_HR_ADMIN",
        "data_scope": DataScopeType.all,             # 显式 all
        ...
    },
    {
        "role_code": "R_DEPT_MGR",
        "data_scope": DataScopeType.department,      # 显式 department
        ...
    },
    {
        "role_code": "R_USER",
        "data_scope": DataScopeType.self_,           # 注意 Python 关键字 → self_
        ...
    },
]
```

> 这条规则在 [`ensure_role`](../../../app/system/services/init_helper.py) 里没有强制（不传就维持原值）——靠 code review。漏写的话部门主管会变成"全公司可见"。

## 业务接口怎么用

```python
from app.utils import CTX_USER_ID, build_scope_filter, get_current_data_scope

async def list_employees_with_relations(search_in: EmployeeSearch, redis=None):
    q = employee_controller.build_search(search_in, contains_fields=[...])

    scope = await get_current_data_scope(redis)
    scope_q = build_scope_filter(
        scope=scope,
        user_id=CTX_USER_ID.get(),
        department_id=get_department_id(),     # 业务模块自带的 ContextVar 工具
        user_id_field="user_id",               # 模型中用户字段名
        dept_id_field="department_id",         # 模型中部门字段名
    )
    total, employees = await employee_controller.list(..., search=q & scope_q)
    return total, records
```

`build_scope_filter`：

| 入参 | scope 命中 → 行为 |
|---|---|
| `is_super_admin()` 或 `scope == "all"` | 返回空 `Q()`，不过滤 |
| `scope == "department"` 且 `department_id` 不为空 | `Q(department_id=...)` |
| 其他（含 `self` / `custom`） | `Q(user_id=...)` |

字段名通过 `user_id_field` / `dept_id_field` 参数指定，不强制为 `user_id` / `department_id`。

## 模块怎么提供 department_id

业务模块通常用一个本模块的 ContextVar + 依赖来注入"当前用户的部门 ID"：

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
# app/business/hr/dependency.py — 在 router 上挂的依赖
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

这样所有 HR 路由进入 service 时 `get_department_id()` 都能拿到正确值。

## Redis 失败时降级

`get_current_data_scope(redis=None)` 会回退到 DB 查询（`Role.filter(role_code__in=...)`）。生产环境 Redis 故障时数据范围依然生效，只是性能下降。

## 哪些资源应当受 scope 限制

不需要给所有表都加 scope。判断标准：

- **强 scope**：员工档案、订单、客户等"含个人或部门归属"的业务表
- **不需要**：字典、菜单、角色、按钮等系统配置类（用 RBAC 即可）
- **慎用**：日志类（按 `actor_id` 限制可能让管理员看不到完整审计链）

## 与 `CRUDRouter` 的关系

`CRUDRouter` 默认的 `list` 路由不加 scope（它不知道你的字段叫什么）。涉及行级权限的资源请 `@override("list")`：

```python
@emp_crud.override("list")
async def _list(obj_in: EmployeeSearch, request: Request):
    total, records = await list_employees_with_relations(obj_in, redis=request.app.state.redis)
    return SuccessExtra(data={"records": records}, total=total, current=obj_in.current, size=obj_in.size)
```

## 与接口级权限的关系

`data_scope` 管的是"同一接口下能看到哪些行"；接口本身"能不能调"由 `DependPermission` 按 `(method, APIRoute.path_format)` 精确判定。两层互补、独立：

- `DependPermission` 的键是 FastAPI 匹配到的路由模板——`/resources/{id}` 和 `/resources/sync` 是两条完全独立的权限记录，不会互相蹭权限。详见 [RBAC / 匹配语义](./rbac.md#匹配语义按-path_format-精确命中)。
- 在 `@crud.override("list")` 里拼 `build_scope_filter(...)` 时不需要再检查调用者是否有该接口的权限——`DependPermission` 已经在进入 handler 前挡住未授权访问。

## 相关

- [RBAC 模型](./rbac.md)
- [HR 模块（行级权限完整实例）](./business-hr.md)
- [缓存](../ops/cache.md) — `role:{code}:data_scope`
