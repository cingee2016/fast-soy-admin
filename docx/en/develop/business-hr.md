# HR Module (first business module)

The first complete business module under `app/business/`, demonstrating **how a business module should be organized** in FastSoyAdmin: autodiscover, menu / role / button declarations, standard + extended `CRUDRouter` usage, state machine, row-level data scope, and frontend button gating.

> Source: `app/business/hr/`, `web/src/views/hr/`
> Target reader: developers adding new business modules to this repo.

## Module scope

HR manages three resources:

- **Department** (`Department`, tree + soft delete + status)
- **Tag** (`Tag`, employee skill / interest dictionary; category references the system dictionary `tag_category`)
- **Employee** (`Employee`, with state machine: `pending → onboarding → active → resigned`)

Four sets of endpoints:

| Audience | Routes | File |
|---|---|---|
| Admin (HR director) | `/hr/departments/*`, `/hr/employees/*`, `/hr/tags/*` | `api/manage.py` |
| Department manager — manage subordinates | `/hr/team/employees/*`, `/hr/team/stats` | `api/team.py` |
| Self-service for employees | `/hr/my/profile`, `/hr/my/avatar`, `/hr/my/tags`, `/hr/my/department` | `api/my.py` |
| Public showcase (constant route demo) | `/hr/public/showcase` | `api/public.py` |

## Directory layout (module convention)

```
app/business/hr/
├── __init__.py
├── config.py          # BIZ_SETTINGS (per-module Pydantic Settings)
├── ctx.py             # module ContextVars (e.g. get_department_id)
├── dependency.py      # module FastAPI deps (DependEmployee / DependManager)
├── models.py          # Tortoise models + state enums
├── schemas.py         # Pydantic schemas (extend SchemaBase)
├── controllers.py     # CRUDBase subclasses (single-resource CRUD)
├── services.py        # multi-model orchestration, cache, FSM
├── events.py          # module event subscriptions
├── init_data.py       # async def init() — menus / roles / buttons / seeds
└── api/
    ├── __init__.py    # must export the aggregated router
    ├── manage.py      # admin routes (HR director)
    ├── team.py        # dept-manager routes (manage subordinates)
    ├── my.py          # self-service routes
    └── public.py      # public constant-route demo
```

`autodiscover` scans `app/business/<name>/` at startup with these rules (see `app/core/autodiscover.py`):

| Rule | Capability |
|---|---|
| `models.py` or `models/` | Tortoise models → registered in `TORTOISE_ORM["apps"]` |
| `router: APIRouter` in `api/` or `api.py` | mounted under `/api/v1/business/` |
| `async def init()` in `init_data.py` | runs after system init, before cache refresh |

A business module **must not** reverse-import sibling business modules or `app.system.*` internals. `system → business` is one-way.

## Data models

### Department

```python
class Department(BaseModel, AuditMixin, TreeMixin, SoftDeleteMixin):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=100, unique=True)
    code = fields.CharField(max_length=50, unique=True)
    description = fields.CharField(max_length=500, null=True)
    status = fields.CharEnumField(enum_type=StatusType, default=StatusType.enable)
    manager_id = fields.IntField(null=True)  # manager employee id (avoids circular FK)
```

`TreeMixin` provides `parent_id / order / level`; combined with `CRUDRouter(tree_endpoint=True)` it auto-generates `GET /departments/tree`.

### Employee

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

> Note `Employee.status` is the **onboarding workflow state**, NOT the generic `enable / disable` dictionary. The frontend has a dedicated `employeeStatusRecord` (in `web/src/constants/business.ts`).

## Permission model (HR's core design)

### Three role tiers

| Role | data_scope | HR buttons | Business positioning |
|---|---|---|---|
| `R_SUPER` | all (auto bypass) | all | system super admin |
| `R_HR_ADMIN` | `all` | all 10 HR buttons | HR director / specialist |
| `R_DEPT_MGR` | `department` | `B_HR_EMP_CREATE / EDIT / TRANSITION` | any department manager |
| `R_USER` | `self` | none | regular employee, uses `/hr/my/*` |

`R_DEPT_MGR` is a **generic department-manager role** — every department's manager uses the same role_code; row-level isolation comes from `data_scope=department` + `Employee.user_id`.

### Button granularity (resource × action)

Button code: `B_HR_<RESOURCE>_<ACTION>`:

| Code | Description | Mounted on |
|---|---|---|
| `B_HR_DEPT_CREATE / _EDIT / _DELETE` | Department create / edit / delete | `hr_department` |
| `B_HR_EMP_CREATE / _EDIT / _DELETE` | Employee create / edit / delete | `hr_employee` |
| `B_HR_EMP_TRANSITION` | Employee state transition | `hr_employee` |
| `B_HR_TAG_CREATE / _EDIT / _DELETE` | Tag create / edit / delete | `hr_tag` |

"Read list" doesn't need a button — gated by menu visibility + API authorization. Batch delete reuses the single-delete code.

### Role × button matrix

| Button | SUPER | R_HR_ADMIN | R_DEPT_MGR | R_USER |
|---|---|---|---|---|
| `B_HR_DEPT_*` | ✅ | ✅ | ❌ | ❌ |
| `B_HR_TAG_*` | ✅ | ✅ | ❌ | ❌ |
| `B_HR_EMP_CREATE` | ✅ | ✅ | ✅ | ❌ |
| `B_HR_EMP_EDIT` | ✅ | ✅ | ✅ (row-scoped to own dept) | ❌ |
| `B_HR_EMP_TRANSITION` | ✅ | ✅ | ✅ | ❌ |
| `B_HR_EMP_DELETE` | ✅ | ✅ | ❌ (workflow-wise `resigned` suffices) | ❌ |

### Backend wiring

Write endpoints declare required buttons via decorator; checked by `require_buttons` at request time:

```python
# app/business/hr/api/manage.py
@router.post(
    "/employees",
    summary="Create employee",
    dependencies=[require_buttons("B_HR_EMP_CREATE")],
)
async def create_emp(...): ...
```

`CRUDRouter` provides `action_dependencies` to bulk-attach by route name (`create / update / delete / batch_delete`):

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

> `action_dependencies` apply to `@override`-replaced routes too — so customizations can't accidentally drop the permission check.

### Frontend wiring

Once button codes are surfaced to the frontend, templates use `hasAuth(...)` to gate visibility. For the actual frontend syntax see [Frontend / Hooks / useTable / Pair with permission buttons](/en/frontend/hooks/use-table#pair-with-permission-buttons); a full example lives in `web/src/views/hr/employee/index.vue`.

## Row-level data scope

### Role field

`Role` has a `data_scope` field; enum in `app/core/data_scope.py`:

- `all` — all data (no filter)
- `department` — own department only
- `self` — self only
- `custom` — reserved; currently falls back to `self`

### init_data must declare data_scope explicitly

`ensure_role()` accepts `data_scope: DataScopeType | None`; **omitting** keeps the model default `all` — an implicit "all-visible" that's wrong for dept managers / regular users. **Business roles always declare it explicitly**:

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

### Service-level usage

Business endpoints stitch the scope filter into their query:

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

Multi-role: most permissive wins. A user holding both `R_HR_ADMIN`(all) and `R_DEPT_MGR`(department) ends up with `all`.

## State machine: employee state transitions

`app/business/hr/services.py` declares legal transitions via `StateMachine`:

```python
EMPLOYEE_FSM = StateMachine(
    transitions={
        "pending":    ["onboarding"],
        "onboarding": ["active"],
        "active":     ["resigned"],
        "resigned":   [],  # terminal
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
    return Success(msg="state updated", ...)
```

The frontend **dynamically** renders the next-action button based on the current state (not a fixed enable/disable toggle):

| Current | Next | Button label |
|---|---|---|
| `pending` | `onboarding` | "Start onboarding" |
| `onboarding` | `active` | "Confirm" |
| `active` | `resigned` | "Resign" |
| `resigned` | — | (no button; terminal) |

Mapping table: `web/src/constants/business.ts` (`employeeNextStatus` / `employeeTransitionLabel`).

## Startup init_data overview

`app/business/hr/init_data.py`'s `init()` runs in order:

```python
async def init():
    await _init_menu_data()      # menus + buttons
    await _init_role_data()      # roles (incl. data_scope + apis grants)
    await _init_departments()    # 5 departments
    await _init_tags()           # 8 tags
    await _init_demo_employees() # 9 employees + manager back-fill
```

### Menus & buttons (declarative + reconciliation)

`HR_MENU_CHILDREN` is the single source of truth for menus / buttons:

```python
HR_MENU_CHILDREN = [
    {
        "menu_name": "Departments", "route_name": "hr_department", "route_path": "/hr/department",
        "buttons": [
            {"button_code": "B_HR_DEPT_CREATE", "button_desc": "create"},
            {"button_code": "B_HR_DEPT_EDIT",   "button_desc": "edit"},
            {"button_code": "B_HR_DEPT_DELETE", "button_desc": "delete"},
        ],
    },
    {"menu_name": "Employees", ..., "buttons": [...]},
    {"menu_name": "Tags",      ..., "buttons": [...]},
]


async def _init_menu_data() -> None:
    await ensure_menu(menu_name="HR", route_name="hr", ..., children=HR_MENU_CHILDREN)
    # Subtree's source of truth is init_data; menus / buttons removed from the seed get reaped on restart
    await reconcile_menu_subtree(
        root_route="hr",
        declared_route_names=_collect_declared_routes(HR_MENU_CHILDREN),
        declared_button_codes=_collect_declared_buttons(HR_MENU_CHILDREN),
    )
```

> Once `reconcile_menu_subtree` is enabled, **the subtree is treated as IaC** — Web-UI-created menus / buttons under it are reaped on next restart. See [Init data](/en/develop/init-data).

### Demo data

| Resource | Count | Notes |
|---|---|---|
| Department | 5 | TECH / MKT / OPS / PERSONNEL / FINANCE |
| Tag | 8 | Remote, doc-driven, cross-team, ... |
| Employee + system user | 9 | numbers 9001–9009; each has a login (password `123456`) |

Each of the 5 departments has a manager:

| Code | Department | Manager | Roles |
|---|---|---|---|
| TECH | Tech | zhouhang | R_DEPT_MGR |
| MKT | Marketing | linyan | R_DEPT_MGR |
| OPS | Operations | songyu | R_DEPT_MGR |
| PERSONNEL | HR | hanmei | **R_HR_ADMIN + R_DEPT_MGR** |
| FINANCE | Finance | qinfeng | R_DEPT_MGR |

> hanmei holding both roles is **intentional**: as PERSONNEL's manager she gets `R_DEPT_MGR` ("inherit own department" so `B_HR_EMP_CREATE` defaults to her department); as HR director she gets `R_HR_ADMIN` (all buttons + `data_scope=all`). Most-permissive wins → company-wide visibility + full button set.

### Business seed sync semantics

- `_safe_update_or_create` upserts by unique key — **inserts/updates fields, never deletes**
- Removing an entry from the seed does **not** clean the DB — write a migration
- Removing a role from the seed does **not** clean the `Role` row; only menus / buttons can be reaped (via `reconcile_menu_subtree`)

## API design highlights

### 1. Use CRUDRouter to kill boilerplate

Department and tag CRUD are templated — declare with one `CRUDRouter`:

```python
tag_crud = CRUDRouter(
    prefix="/tags",
    controller=tag_controller,
    create_schema=TagCreate,
    update_schema=TagUpdate,
    list_schema=TagSearch,
    search_fields=SearchFieldConfig(contains_fields=["name"], exact_fields=["category"]),
    summary_prefix="Tag",
    action_dependencies={
        "create":       [require_buttons("B_HR_TAG_CREATE")],
        "update":       [require_buttons("B_HR_TAG_EDIT")],
        "delete":       [require_buttons("B_HR_TAG_DELETE")],
        "batch_delete": [require_buttons("B_HR_TAG_DELETE")],
    },
)
```

### 2. `@override` for routes that need custom logic

Employee `list / get` need `select_related / prefetch_related` to avoid N+1 + row-level scope:

```python
emp_crud = CRUDRouter(
    prefix="/employees",
    controller=employee_controller,
    list_schema=EmployeeSearch,
    summary_prefix="Employee",
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

> `emp_crud` doesn't pass `create_schema / update_schema`, so `CRUDRouter` doesn't register the default `POST/PATCH /employees` — leaving room for the hand-written ones below.

### 3. Create employee: service handles cross-model orchestration

Creating an employee chains **system user creation + employee + tag association**, so it goes through services:

```python
@router.post(
    "/employees",
    summary="Create employee",
    dependencies=[require_buttons("B_HR_EMP_CREATE")],
)
async def create_emp(emp_in: EmployeeCreate, request: Request):
    current_emp = await employee_controller.get_or_none(user_id=CTX_USER_ID.get())
    return await create_employee(emp_in, current_emp, request.app.state.redis)
```

`create_employee` distinguishes three callers:

```python
# Super admin / HR admin (holds B_HR_EMP_CREATE, no employee binding) → must specify department
if is_super_admin() or (has_button_code("B_HR_EMP_CREATE") and not current_emp):
    if not emp_in.department_id:
        return Fail(code=Code.HR_DEPARTMENT_REQUIRED, msg="department required")
# Department manager (holds B_HR_EMP_CREATE and is bound as a manager) → auto inherit own department
elif has_button_code("B_HR_EMP_CREATE") and current_emp:
    dept = await Department.filter(manager_id=current_emp.id).first()
    if not dept:
        return Fail(code=Code.HR_MANAGER_REQUIRED, msg="manager only")
    emp_in.department_id = dept.id
else:
    return Fail(code=Code.HR_CREATE_FORBIDDEN, msg="no permission")
```

Then in a transaction: create the system user (random password + `must_change_password`), employee, tag associations, and `emit("employee.created", ...)`.

### 4. Cache & invalidation

Standard pattern for **module-local caching**: name keys `<module>_<resource>:<scope>`; on read, miss → query → write with TTL; on data change, invalidate explicitly via `redis.delete(...)`. The live in-repo reference is the dictionary-options cache ([`app/system/api/dictionary.py`](../../app/system/api/dictionary.py.md), keys like `dict_options:<type>`).

### 5. Public endpoint (constant route example)

`api/public.py` exposes endpoints that **bypass auth entirely**, used by the frontend's constant route (`/showcase`) — accessible without login, returning only aggregated stats with no sensitive fields. Live demo: <https://fast-soy-admin.sleep0.de/showcase>.

```python
# app/business/hr/api/public.py
router = APIRouter(prefix="/hr/public", tags=["HR Public Showcase"])

@router.get("/showcase", summary="[Public] HR data overview")
async def showcase_overview():
    return Success(data={
        "totals": {"department": ..., "employee": ..., "tag": ...},
        "employeeStatus": {...},
        "departments": [{"name": ..., "code": ..., "employeeCount": ...}],
    })
```

Frontend counterparts:

- View: [web/src/views/showcase/index.vue](../../web/src/views/showcase/index.vue.md)
- API call: `fetchGetHrShowcase()` ([web/src/service/api/hr-manage.ts](../../web/src/service/api/hr-manage.ts.md))
- Route config: `web/src/router/elegant/routes.ts` with `name: 'showcase'` + `meta.constant: true` + `component: 'layout.blank$view.showcase'`
- Constant route whitelist: `'showcase'` is added to `constantRoutes` in `web/build/plugins/router.ts`

#### Backend must also seed a `Menu` row (important)

By default `VITE_AUTH_ROUTE_MODE=dynamic`. The frontend calls `GET /api/v1/route/constant-routes` at startup and pulls constant routes from Redis; the data source is `Menu.filter(constant=True, hide_in_menu=True)` (see [load_constant_routes](../../app/core/cache.py.md)). Declaring `meta.constant: true` only on the frontend isn't enough — without a `Menu` row, the backend returns empty, the frontend can't mount the route, and the page 404s.

So `init_data.py` must include:

```python
# app/business/hr/init_data.py
async def _init_menu_data() -> None:
    await ensure_menu(
        menu_name="HR Showcase",
        route_name="showcase",
        route_path="/showcase",
        component="layout.blank$view.showcase",
        menu_type="1",
        constant=True,
        hide_in_menu=True,
        order=100,
    )
    # ...other menus
```

Startup pipeline: `init()` → write the `Menu` row → `refresh_all_cache()` → `load_constant_routes()` rewrites the Redis `constant_routes` key → frontend picks it up next startup. **Restart the backend after adding a constant route.**

> Under `VITE_AUTH_ROUTE_MODE=static` (frontend ships all route declarations itself) only the frontend-side change is needed; this repo defaults to dynamic, don't skip the backend step.

## Use HR as a template for new modules

To create a new business module (e.g. `crm`), copy HR's structure:

```bash
cp -r app/business/hr app/business/crm
# Update: model table prefix, menu route_name, role role_code, button button_code, API prefix
```

Must-do checklist:

1. **Menus / buttons / roles are single-sourced from `init_data.py`** — add / delete / rename via seeds + restart reconciliation
2. **Each role declares `data_scope` explicitly** — never rely on the default `all`
3. **Write endpoints attach button permissions** (`require_buttons` or `action_dependencies`) — never rely on hidden buttons for security
4. **Frontend buttons all use `hasAuth(...)`** — 1:1 with backend button codes
5. **Watch `ensure_role` warnings** when removing button codes / route names — `missing buttons / missing apis` warnings indicate seeds are out of sync with code

## Related

- [Init data](/en/develop/init-data) — `ensure_menu / ensure_role / reconcile_menu_subtree` semantics
- [Auth](/en/develop/auth) — JWT, dependencies, button permissions
- [CRUDBase](/en/develop/crud) — `CRUDBase / build_search / SearchFieldConfig`
- [API conventions](/en/develop/api) — paths / methods / response format
