# HR 管理（第一个子业务模块）

HR 模块是 `app/business/` 下第一个完整业务模块，演示业务模块在 FastSoyAdmin 中**应当如何组织**：自动发现、菜单/角色/按钮声明、CRUDRouter 的标准与扩展用法、状态机、行级数据权限、前端按钮鉴权。

> 源码位置：[app/business/hr/](../../../app/business/hr/)、[web/src/views/hr/](../../../web/src/views/hr/)
> 适合阅读对象：在本仓库新增业务模块的开发者。

## 模块定位

HR 模块管理三类资源：

- **部门**（`Department`，树形结构 + 软删除 + 状态字段）
- **标签**（`Tag`，员工技能/特长字典，分类引用系统字典 `tag_category`）
- **员工**（`Employee`，含状态机：`pending → onboarding → active → resigned`）

并暴露四套接口：

| 角色场景 | 路由 | 文件 |
|---|---|---|
| 系统管理（HR 总管） | `/hr/departments/*`、`/hr/employees/*`、`/hr/tags/*` | [api/manage.py](../../../app/business/hr/api/manage.py) |
| 部门主管管理下属 | `/hr/team/employees/*`、`/hr/team/stats` | [api/team.py](../../../app/business/hr/api/team.py) |
| 普通员工自助 | `/hr/my/profile`、`/hr/my/avatar`、`/hr/my/tags`、`/hr/my/department` | [api/my.py](../../../app/business/hr/api/my.py) |
| 公开数据展示（常量路由 Demo） | `/hr/public/showcase` | [api/public.py](../../../app/business/hr/api/public.py) |

## 目录结构（业务模块约定）

```
app/business/hr/
├── __init__.py
├── config.py          # BIZ_SETTINGS（按模块隔离的 Pydantic Settings）
├── ctx.py             # 模块上下文变量（如 get_department_id）
├── dependency.py      # 模块 FastAPI 依赖（DependEmployee / DependManager）
├── models.py          # Tortoise 模型 + 状态枚举
├── schemas.py         # Pydantic schema（继承 SchemaBase）
├── controllers.py     # CRUDBase 子类（单资源 CRUD）
├── services.py        # 多模型编排、缓存、状态机
├── events.py          # 模块事件订阅
├── init_data.py       # async def init() — 菜单 / 角色 / 按钮 / 种子
└── api/
    ├── __init__.py    # 必须导出汇总后的 router
    ├── manage.py      # 系统管理路由（HR 总管）
    ├── team.py        # 部门主管路由（管理下属）
    ├── my.py          # 员工自助路由
    └── public.py      # 公开常量路由示例
```

`autodiscover` 在启动时扫描 `app/business/<name>/`，按以下约定加载（详见 [app/core/autodiscover.py](../../../app/core/autodiscover.py)）：

| 约定 | 提供的能力 |
|---|---|
| `models.py` 或 `models/` | Tortoise 模型 → 注册到 `TORTOISE_ORM["apps"]` |
| `api/` 或 `api.py` 中的 `router: APIRouter` | 挂载到 `/api/v1/business/` |
| `init_data.py` 中的 `async def init()` | 在系统初始化之后、缓存刷新之前执行 |

业务模块**不得反向 import** `app.system.*` 之外的兄弟业务模块。`system → business` 是单向依赖。

## 数据模型

### 部门 Department

```python
class Department(BaseModel, AuditMixin, TreeMixin, SoftDeleteMixin):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=100, unique=True)
    code = fields.CharField(max_length=50, unique=True)
    description = fields.CharField(max_length=500, null=True)
    status = fields.CharEnumField(enum_type=StatusType, default=StatusType.enable)
    manager_id = fields.IntField(null=True)  # 主管员工 ID（避免循环 FK）
```

`TreeMixin` 提供 `parent_id / order / level`，配合 `CRUDRouter(tree_endpoint=True)` 自动生成 `GET /departments/tree`。

### 员工 Employee

```python
class EmployeeStatus(str, Enum):
    pending = "pending"
    onboarding = "onboarding"
    active = "active"
    resigned = "resigned"


class Employee(BaseModel, AuditMixin, SoftDeleteMixin):
    employee_no = fields.CharField(max_length=20, unique=True)
    status = fields.CharEnumField(enum_type=EmployeeStatus, default=EmployeeStatus.pending)
    user: fields.ForeignKeyNullableRelation = fields.ForeignKeyField(
        "app_system.User", null=True, unique=True, on_delete=fields.SET_NULL
    )
    department: fields.ForeignKeyRelation[Department] = fields.ForeignKeyField(
        "app_system.Department", related_name="employees"
    )
    tags: fields.ManyToManyRelation[Tag] = fields.ManyToManyField(
        "app_system.Tag", related_name="employees"
    )
```

> 注意 `Employee.status` 是**入职流程状态**，不是系统通用的"启用/禁用"字典。前端有专属 `employeeStatusRecord`（位于 [web/src/constants/business.ts](../../../web/src/constants/business.ts)）。

## 权限模型（这是 HR 模块的核心设计）

### 三层角色

| 角色 | data_scope | HR 按钮 | 业务定位 |
|---|---|---|---|
| `R_SUPER` | all（自动跳过过滤） | 全部 | 系统超管 |
| `R_HR_ADMIN` | `all` | 10 个 HR 按钮全集 | HR 总管 / 人事专员 |
| `R_DEPT_MGR` | `department` | `B_HR_EMP_CREATE / EDIT / TRANSITION` | 任意部门主管 |
| `R_USER` | `self` | 无 | 普通员工，走 `/hr/my/*` |

`R_DEPT_MGR` 是**通用部门主管角色**——所有部门的主管都用同一个 role_code，靠 `data_scope=department` + `Employee.user_id` 做行级隔离。

### 按钮粒度（资源 × 操作）

按钮码采用 `B_HR_<RESOURCE>_<ACTION>` 命名：

| 按钮码 | 描述 | 挂在哪个菜单 |
|---|---|---|
| `B_HR_DEPT_CREATE / _EDIT / _DELETE` | 部门 增 / 改 / 删 | `hr_department` |
| `B_HR_EMP_CREATE / _EDIT / _DELETE` | 员工 增 / 改 / 删 | `hr_employee` |
| `B_HR_EMP_TRANSITION` | 员工状态流转 | `hr_employee` |
| `B_HR_TAG_CREATE / _EDIT / _DELETE` | 标签 增 / 改 / 删 | `hr_tag` |

「读列表」不发按钮——通过菜单可见 + API 授权控制。批量删除复用单删按钮码。

### 角色 × 按钮 矩阵

| 按钮 | SUPER | R_HR_ADMIN | R_DEPT_MGR | R_USER |
|---|---|---|---|---|
| `B_HR_DEPT_*` | ✅ | ✅ | ❌ | ❌ |
| `B_HR_TAG_*` | ✅ | ✅ | ❌ | ❌ |
| `B_HR_EMP_CREATE` | ✅ | ✅ | ✅ | ❌ |
| `B_HR_EMP_EDIT` | ✅ | ✅ | ✅（行级限本部门） | ❌ |
| `B_HR_EMP_TRANSITION` | ✅ | ✅ | ✅ | ❌ |
| `B_HR_EMP_DELETE` | ✅ | ✅ | ❌（流程上 `resigned` 即可） | ❌ |

### 后端怎么挂权限

写接口在装饰器上声明所需按钮，由 [require_buttons](../../../app/core/dependency.py) 在请求阶段校验：

```python
# app/business/hr/api/manage.py
@router.post(
    "/employees",
    summary="创建员工",
    dependencies=[require_buttons("B_HR_EMP_CREATE")],
)
async def create_emp(...): ...
```

CRUDRouter 提供 `action_dependencies`，按路由名（`create / update / delete / batch_delete`）批量挂依赖：

```python
dept_crud = CRUDRouter(
    prefix="/departments",
    controller=department_controller,
    create_schema=DepartmentCreate,
    update_schema=DepartmentUpdate,
    list_schema=DepartmentSearch,
    soft_delete=True,
    tree_endpoint=True,
    action_dependencies={
        "create":       [require_buttons("B_HR_DEPT_CREATE")],
        "update":       [require_buttons("B_HR_DEPT_EDIT")],
        "delete":       [require_buttons("B_HR_DEPT_DELETE")],
        "batch_delete": [require_buttons("B_HR_DEPT_DELETE")],
    },
)
```

> `action_dependencies` 对 `@override` 替换的路由同样生效，所以在前缀模板上挂的依赖不会被自定义实现"漏掉"。

### 前端怎么挂权限

按钮码透传到前端后，模板里用 `hasAuth(...)` 控制按钮可见性。前端用法详见 [前端 / Hooks / useTable](../frontend/hooks/use-table.md#配合权限按钮)，完整样例在 [web/src/views/hr/employee/index.vue](../../../web/src/views/hr/employee/index.vue)。

## 行级数据权限（data_scope）

### 角色字段

`Role` 模型有 `data_scope` 字段，枚举见 [app/core/data_scope.py](../../../app/core/data_scope.py)：

- `all` — 全部数据（不过滤）
- `department` — 仅本部门数据
- `self` — 仅本人数据
- `custom` — 预留，当前降级到 `self`

### init_data 必须显式声明 data_scope

`ensure_role()` 接收 `data_scope: DataScopeType | None`，**不传**则使用 `Role` 模型默认值 `all` —— 这是个隐式的"全可见"，对部门主管/普通用户来说是错误的。**业务角色一律显式声明**：

```python
# app/business/hr/init_data.py
HR_ROLE_SEEDS = [
    {
        "role_code": "R_HR_ADMIN",
        "data_scope": DataScopeType.all,
        ...
    },
    {
        "role_code": "R_DEPT_MGR",
        "data_scope": DataScopeType.department,
        ...
    },
]
```

### service 层使用方式

业务接口在构建查询时拼入 scope 条件：

```python
# app/business/hr/services.py
async def list_employees_with_relations(search_in: EmployeeSearch, redis=None):
    q = employee_controller.build_search(search_in, ...)

    scope = await get_current_data_scope(redis)
    scope_q = build_scope_filter(
        scope=scope,
        user_id=CTX_USER_ID.get(),
        department_id=get_department_id(),
    )
    total, employees = await employee_controller.list(..., search=q & scope_q)
    return total, records
```

多角色取最宽松：用户同时持有 `R_HR_ADMIN`(all) 和 `R_DEPT_MGR`(department) 时，最终生效 `all`。

## 状态机：员工状态流转

[app/business/hr/services.py](../../../app/business/hr/services.py) 用 [StateMachine](../../../app/core/state_machine.py) 声明合法转移：

```python
EMPLOYEE_FSM = StateMachine(
    transitions={
        "pending":    ["onboarding"],
        "onboarding": ["active"],
        "active":     ["resigned"],
        "resigned":   [],  # 终态
    }
)


async def transition_employee(emp_id: int, to_state: str):
    emp = await employee_controller.get(id=emp_id)
    await EMPLOYEE_FSM.transition(
        obj=emp,
        to_state=to_state,
        state_field="status",
        actor_id=get_current_user_id(),
        log_fn=radar_log,
    )
    await emit("employee.status_changed", employee_id=emp_id, ...)
    return Success(msg="状态更新成功", ...)
```

前端按当前状态**动态展示**下一步动作（不是固定的"启用/禁用"切换）：

| 当前 | 下一状态 | 按钮文案 |
|---|---|---|
| `pending` | `onboarding` | 办理入职 |
| `onboarding` | `active` | 确认转正 |
| `active` | `resigned` | 办理离职 |
| `resigned` | — | （不显示按钮，终态） |

映射表见 [web/src/constants/business.ts](../../../web/src/constants/business.ts)（`employeeNextStatus` / `employeeTransitionLabel`）。

## 启动 init_data 全景

[app/business/hr/init_data.py](../../../app/business/hr/init_data.py) 在 `init()` 中按顺序执行：

```python
async def init():
    await _init_menu_data()      # 菜单 + 按钮
    await _init_role_data()      # 角色（含 data_scope + apis 授权）
    await _init_departments()    # 5 个部门
    await _init_tags()           # 8 个标签
    await _init_demo_employees() # 9 个员工 + 主管反向回填
```

### 菜单与按钮（声明 + 对账）

`HR_MENU_CHILDREN` 是菜单/按钮的 single-source-of-truth：

```python
HR_MENU_CHILDREN = [
    {
        "menu_name": "部门管理", "route_name": "hr_department", "route_path": "/hr/department",
        "buttons": [
            {"button_code": "B_HR_DEPT_CREATE", "button_desc": "创建部门"},
            {"button_code": "B_HR_DEPT_EDIT",   "button_desc": "编辑部门"},
            {"button_code": "B_HR_DEPT_DELETE", "button_desc": "删除部门"},
        ],
    },
    {"menu_name": "员工管理", ..., "buttons": [...]},
    {"menu_name": "标签管理", ..., "buttons": [...]},
]


async def _init_menu_data() -> None:
    await ensure_menu(menu_name="HR管理", route_name="hr", ..., children=HR_MENU_CHILDREN)
    # 子树以 init_data 为权威源；从 seed 删除的菜单/按钮在重启时被清除
    await reconcile_menu_subtree(
        root_route="hr",
        declared_route_names=_collect_declared_routes(HR_MENU_CHILDREN),
        declared_button_codes=_collect_declared_buttons(HR_MENU_CHILDREN),
    )
```

> 一旦启用 `reconcile_menu_subtree`，**该子树就被视为 IaC（基础设施即代码）**——通过 Web UI 在该子树下手工创建的菜单/按钮会在下次重启时被清除。详见 [启动初始化与对账](./init-data.md)。

### 演示数据规模

| 资源 | 数量 | 说明 |
|---|---|---|
| 部门 | 5 | TECH / MKT / OPS / PERSONNEL / FINANCE |
| 标签 | 8 | 远程协作 / 文档驱动 / 跨部门协作 / … |
| 员工 + 系统用户 | 9 | 工号 9001 ~ 9009，每人对应一个登录账号（密码 `123456`） |

5 个部门各有一名主管：

| 编码 | 部门 | 主管 | 角色 |
|---|---|---|---|
| TECH | 技术部 | 周航 (zhouhang) | R_DEPT_MGR |
| MKT | 市场部 | 林妍 (linyan) | R_DEPT_MGR |
| OPS | 行政部 | 宋羽 (songyu) | R_DEPT_MGR |
| PERSONNEL | 人事部 | 韩梅 (hanmei) | **R_HR_ADMIN + R_DEPT_MGR** |
| FINANCE | 财务部 | 秦风 (qinfeng) | R_DEPT_MGR |

> 韩梅同时挂两个角色是**有意为之**：身份上她是人事部主管（R_DEPT_MGR 提供"本部门数据继承"，便于通过 `B_HR_EMP_CREATE` 自动落到本部门），职责上她是 HR 总管（R_HR_ADMIN 提供全公司按钮 + `data_scope=all`）。多角色取最宽松，最终效果是全公司可见 + 全按钮可用。

### 业务种子数据的同步语义

- 通过 `_safe_update_or_create` 按唯一键 upsert，**只新增/改字段，不删**。
- 从 seed 中删除一条记录，DB 中**不会**自动清理——需要走迁移。
- 删除 seed 中的角色，对应 `Role` 行也不会被清理；删除菜单/按钮才会（依赖 `reconcile_menu_subtree`）。

## API 设计要点

### 1. 用 CRUDRouter 把样板代码消灭掉

部门和标签的 CRUD 完全是模板化的，直接用 `CRUDRouter` 一句声明：

```python
tag_crud = CRUDRouter(
    prefix="/tags",
    controller=tag_controller,
    create_schema=TagCreate,
    update_schema=TagUpdate,
    list_schema=TagSearch,
    search_fields=SearchFieldConfig(contains_fields=["name"], exact_fields=["category"]),
    summary_prefix="标签",
    action_dependencies={
        "create":       [require_buttons("B_HR_TAG_CREATE")],
        "update":       [require_buttons("B_HR_TAG_EDIT")],
        "delete":       [require_buttons("B_HR_TAG_DELETE")],
        "batch_delete": [require_buttons("B_HR_TAG_DELETE")],
    },
)
```

### 2. 用 `@override` 替换需要自定义逻辑的路由

员工的 `list / get` 需要 `select_related / prefetch_related` 优化 N+1 + 行级 scope 过滤：

```python
emp_crud = CRUDRouter(
    prefix="/employees",
    controller=employee_controller,
    list_schema=EmployeeSearch,
    summary_prefix="员工",
    soft_delete=True,
    action_dependencies={
        "delete":       [require_buttons("B_HR_EMP_DELETE")],
        "batch_delete": [require_buttons("B_HR_EMP_DELETE")],
    },
)


@emp_crud.override("list")
async def _list_employees(obj_in: EmployeeSearch, request: Request):
    total, records = await list_employees_with_relations(obj_in, redis=request.app.state.redis)
    return SuccessExtra(data={"records": records}, total=total, current=obj_in.current, size=obj_in.size)


@emp_crud.override("get")
async def _get_employee(item_id: SqidPath):
    emp = await employee_controller.get(id=item_id)
    await emp.fetch_related("department", "tags")
    record = await emp.to_dict()
    record["departmentName"] = emp.department.name
    record["tagIds"]   = [t.id   for t in emp.tags]
    record["tagNames"] = [t.name for t in emp.tags]
    return Success(data=record)
```

> `emp_crud` 没有传 `create_schema / update_schema`，CRUDRouter 不会注册默认的 `POST/PATCH /employees` 路由——所以下面的手写 `@router.post / @router.patch` 不会被遮蔽。

### 3. 创建员工：service 层处理多模型编排

创建员工要联动**创建系统用户 + 员工 + 标签关联**，所以走 service 层：

```python
@router.post(
    "/employees",
    summary="创建员工",
    dependencies=[require_buttons("B_HR_EMP_CREATE")],
)
async def create_emp(emp_in: EmployeeCreate, request: Request):
    current_emp = await employee_controller.get_or_none(user_id=CTX_USER_ID.get())
    return await create_employee(emp_in, current_emp, request.app.state.redis)
```

`create_employee` 区分三类调用方：

```python
# 超级管理员 / HR 管理员（持 B_HR_EMP_CREATE 但未绑定员工）→ 必须显式指定部门
if is_super_admin() or (has_button_code("B_HR_EMP_CREATE") and not current_emp):
    if not emp_in.department_id:
        return Fail(code=Code.HR_DEPARTMENT_REQUIRED, msg="创建员工需要指定部门")
# 部门主管（持 B_HR_EMP_CREATE 且绑定的员工是某部门主管）→ 自动继承本部门
elif has_button_code("B_HR_EMP_CREATE") and current_emp:
    dept = await Department.filter(manager_id=current_emp.id).first()
    if not dept:
        return Fail(code=Code.HR_MANAGER_REQUIRED, msg="仅部门主管可创建员工")
    emp_in.department_id = dept.id
else:
    return Fail(code=Code.HR_CREATE_FORBIDDEN, msg="无权限创建员工")
```

随后在一个事务里创建系统用户（随机密码 + `must_change_password`）、员工、标签关联，并 `emit("employee.created", ...)` 触发事件。

### 4. 缓存与失效

业务模块**自带缓存**的标准模式：键命名 `<module>_<resource>:<scope>`，读时 miss → 查询 → 写入并设置 TTL，数据变更时主动 `redis.delete(...)` 失效。仓库内可参考的实现为字典选项缓存（[`app/system/api/dictionary.py`](../../../app/system/api/dictionary.py)，键形如 `dict_options:<type>`）。

### 5. 公开接口（常量路由示例）

`api/public.py` 暴露了一组**不经过鉴权**的端点，用于前端的常量路由（`/showcase`）——未登录即可访问，只返回聚合统计，不含任何敏感字段。在线 Demo：<https://fast-soy-admin.sleep0.de/showcase>。

```python
# app/business/hr/api/public.py
router = APIRouter(prefix="/hr/public", tags=["HR公开展示"])

@router.get("/showcase", summary="[公开] HR 数据展示总览")
async def showcase_overview():
    return Success(data={
        "totals": {"department": ..., "employee": ..., "tag": ...},
        "employeeStatus": {...},
        "departments": [{"name": ..., "code": ..., "employeeCount": ...}],
    })
```

对应前端：

- 视图：[web/src/views/showcase/index.vue](../../../web/src/views/showcase/index.vue)
- API 调用：`fetchGetHrShowcase()`（[web/src/service/api/hr-manage.ts](../../../web/src/service/api/hr-manage.ts)）
- 路由配置：`web/src/router/elegant/routes.ts` 中 `name: 'showcase'` + `meta.constant: true` + `component: 'layout.blank$view.showcase'`
- 常量路由白名单：`web/build/plugins/router.ts` 的 `constantRoutes` 中加入了 `'showcase'`

#### 后端也要种一条 `Menu` 记录（重要）

**默认 `VITE_AUTH_ROUTE_MODE=dynamic`**，前端启动时会调用 `GET /api/v1/route/constant-routes` 从 Redis 拉常量路由，数据源是 `Menu.filter(constant=True, hide_in_menu=True)`（详见 [load_constant_routes](../../../app/core/cache.py)）。只在前端声明 `meta.constant: true` 是不够的——不种 `Menu`，后端返回空，前端挂不上路由，访问会 404。

所以 `init_data.py` 里必须配套一条：

```python
# app/business/hr/init_data.py
async def _init_menu_data() -> None:
    await ensure_menu(
        menu_name="HR数据展示",
        route_name="showcase",
        route_path="/showcase",
        component="layout.blank$view.showcase",
        menu_type="1",
        constant=True,
        hide_in_menu=True,
        order=100,
    )
    # ...后续其他菜单
```

启动流水线：`init()` → 写入 `Menu` 记录 → `refresh_all_cache()` → `load_constant_routes()` 重写 Redis `constant_routes` key → 前端下次启动拉到。**新增常量路由后必须重启一次后端**。

> 如果是 `VITE_AUTH_ROUTE_MODE=static`（前端自带全部路由声明），则只需前端那一侧的改动；但本仓库默认是 dynamic，别漏。

**公开接口的铁律：**

1. **不要**在 router 或 endpoint 上挂 `DependAuth` / `DependPermission`
2. **不要**返回包含 PII 的字段（`phone` / `email` / `employee_no` / `user_id`）
3. **不要**返回可用于枚举探测的精确列表（如"所有员工姓名"）——只返回聚合计数
4. 路径统一放在 `/<module>/public/*` 前缀下，便于 nginx / WAF 侧做 IP 限流策略
5. 若数据可能较贵，建议搭配 Redis 缓存（参考字典选项实现 [`app/system/api/dictionary.py`](../../../app/system/api/dictionary.py)）

## 用 HR 模块作为新模块的参考

新建一个业务模块（例如 `crm`）建议照搬 HR 模块的目录与文件命名：

```bash
cp -r app/business/hr app/business/crm
# 修改：模型表名前缀、菜单 route_name、角色 role_code、按钮 button_code、API prefix
```

务必做到的几点：

1. **菜单/按钮/角色一律以 `init_data.py` 为唯一数据源**，新增/删除/重命名走 seed + 重启对账。
2. **每个角色显式声明 `data_scope`**，不要依赖 `Role` 模型默认的 `all`。
3. **写接口必须挂按钮权限**（`require_buttons` 或 `action_dependencies`），不要依赖前端隐藏按钮做安全。
4. **前端按钮一律 `hasAuth(...)`**，与后端按钮码 1:1 对应。
5. **删除按钮码或 route_name 时检查 ensure_role 的 warning 日志**——`ensure_role` 会输出 `missing buttons / missing apis` 警告，提示 seed 列表与代码脱节。

## 相关文档

- [启动初始化与对账](./init-data.md) — `ensure_menu / ensure_role / reconcile_menu_subtree` 的工作机制
- [认证与权限](./auth.md) — JWT、`DependAuth / DependPermission`、按钮权限
- [CRUD 基类](./crud.md) — `CRUDBase / CRUDRouter / SearchFieldConfig`
- [API 路由](./api.md) — 路由约定（路径、命名、响应格式）
