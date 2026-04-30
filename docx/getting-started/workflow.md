# 开发指南

从零新增业务模块的完整流程。CLI 只要求你写 `models.py`，schemas、controllers、API、前端 views、i18n 全自动生成。

## 先决条件

所有命令在项目根目录执行。首次使用先装依赖、建表：

```bash
make install-all     # 后端 + 前端依赖
cp .env.example .env # 复制环境变量模板，按需修改 SECRET_KEY / DB_URL / REDIS_URL 等
make initdb          # 首次建表 + 基础数据
```

## 创建新模块：以 `inventory`（库存管理）为例

### 1. 创建模块骨架

```bash
make cli-init MOD=inventory
# 执行过程中会要求输入模块中文名，如"库存管理"
```

执行后会生成：

```
app/business/inventory/
├── __init__.py
└── models.py          ← 只含常用导入与示例注释
```

### 2. 编辑 `models.py` 定义模型

用编辑器打开 `app/business/inventory/models.py`，按 Tortoise ORM 语法定义模型。**几个约定**：

- 继承 `BaseModel, AuditMixin`
- 每个字段加 `description="..."`（生成的 schema 会自动将其截断到句号前作为 i18n 中文名）
- 类的 docstring 写中文名（`"""仓库"""`），将作为 API summary 前缀
- `Meta.table` 建议使用 `biz_<module>_<entity>` 前缀

```python
# pyright: reportIncompatibleVariableOverride=false
"""库存管理 — 业务模型定义。"""

from tortoise import fields

from app.utils import AuditMixin, BaseModel, StatusType


class Warehouse(BaseModel, AuditMixin):
    """仓库"""

    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=100, unique=True, description="仓库名称")
    code = fields.CharField(max_length=50, unique=True, description="仓库编号")
    address = fields.CharField(max_length=255, null=True, description="地址")
    status = fields.CharEnumField(enum_type=StatusType, default=StatusType.enable, description="状态")

    class Meta:
        table = "biz_inventory_warehouse"
        table_description = "仓库"


class Product(BaseModel, AuditMixin):
    """产品"""

    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=100, description="产品名称")
    sku = fields.CharField(max_length=50, unique=True, description="SKU编号")
    price = fields.DecimalField(max_digits=10, decimal_places=2, description="价格")
    stock = fields.IntField(default=0, description="库存数量")
    status = fields.CharEnumField(enum_type=StatusType, default=StatusType.enable, description="状态")

    warehouse_id: int
    warehouse: fields.ForeignKeyRelation["Warehouse"] = fields.ForeignKeyField(
        "app_system.Warehouse", related_name="products", description="所属仓库"
    )

    class Meta:
        table = "biz_inventory_product"
        table_description = "产品"
```

### 3. 生成后端代码

```bash
make cli-gen MOD=inventory
```

交互式地选择每个模型的模糊搜索字段（可直接回车全选），生成：

```
app/business/inventory/
├── __init__.py
├── models.py
├── schemas.py          # Pydantic Create/Update/Search
├── controllers.py      # CRUDBase 实例
├── services.py         # 业务逻辑占位
├── init_data.py        # 菜单 / 角色 / 种子数据占位
└── api/
    ├── __init__.py
    └── manage.py       # CRUDRouter 自动生成 6 个标准路由
```

生成后会自动跑 `ruff check --fix` + `ruff format`。

### 4. 生成前端代码

```bash
make cli-gen-web MOD=inventory CN=库存管理
```

> 也可以用 `make cli-gen-all MOD=inventory CN=库存管理` 一次跑完步骤 3 和 4。

选择每个模型的**列表展示字段**和**搜索字段**后，生成：

```
web/
├── src/service/api/inventory-manage.ts        # CRUD API 调用
├── src/typings/api/inventory-manage.d.ts      # TS 类型定义
├── src/views/inventory/<entity>/
│   ├── index.vue                              # 列表页
│   └── modules/
│       ├── <entity>-search.vue                # 搜索表单
│       └── <entity>-operate-drawer.vue        # 新增/编辑抽屉
└── src/locales/langs/_generated/inventory/
    ├── zh-cn.ts                               # i18n 中文消息（自动合并，无需手动操作）
    ├── en-us.ts                               # i18n 英文消息（自动合并）
    └── types.d.ts                             # GeneratedPages 类型扩展（declare 合并自动生效）
```

`web/src/service/api/index.ts` 会自动追加 `export * from './inventory-manage';`（幂等）。

生成后会对新增/追加的 `.ts / .tsx / .vue / .d.ts` 文件自动跑 `oxfmt` + `eslint --fix`。

### 5. i18n 自动合并

`_generated/<module>/` 下三个文件由前端工程链自动消费，无需手动编辑全局语言包：

| 文件 | 消费方 | 作用 |
|---|---|---|
| `zh-cn.ts` / `en-us.ts` | [`web/src/locales/locale.ts`](https://github.com/sleep1223/fast-soy-admin/blob/dev/web/src/locales/locale.ts) 通过 `import.meta.glob` 深合并入对应语言的 messages | 注入 `route.<module>` 与 `page.<module>` 子树 |
| `types.d.ts` | TypeScript declaration merging 注入 `App.I18n.GeneratedPages` | 使 `$t('page.<module>.<entity>.xxx')` 受 `vue-tsc` 校验 |

类型层契约：

- `App.I18n.Schema.page` 与 `_MergePages<GeneratedPages>` 取交集，新增模块仅需通过 `interface GeneratedPages { <module>: {...} }` 扩张键空间。
- 基础语言包 `zh-cn.ts` / `en-us.ts` 标注为 `App.I18n.BaseSchema`（即 `Schema` 排除 `GeneratedPages` 部分），新增模块不会要求基础文件补字段。
- `App.I18n.Schema.route` 为 `Partial<Record<I18nRouteKey, string>>`，路由键由 Elegant Router 自 `views/` 推导，对应翻译由 `_generated/<module>/zh-cn.ts` 提供。

### 6. 处理 TODO

前端中的外键 / 自定义枚举无法自动推导数据源，生成代码里留有 `// TODO` 注释。用 IDE 搜索 TODO，补齐 options 的数据源（通常是配置一个 `fetchGetXxxList` 请求）。

### 7. 迁移数据库

```bash
make mm         # == makemigrations + migrate
```

### 8. 启动并验证

```bash
make dev        # 同时起前后端
```

访问 `http://localhost:9527` 登录，进入 `/inventory/warehouse`、`/inventory/product` 验证 CRUD。

### 9. 提交前质量检查

```bash
make check-all  # 后端 + 前端全部质量检查
```

## 字段类型映射速查

CLI 根据 Tortoise 字段类型自动推导 TS 类型和表单组件：

| Tortoise 字段 | TS 类型 | 后端 schema | 前端表单 | 前端搜索 |
|---|---|---|---|---|
| `CharField` | `string` | `str` | `NInput` | `NInput` |
| `TextField` | `string` | `str` | `NInput type="textarea"` | `NInput` |
| `IntField` / `BigIntField` | `number` | `int` | `NInputNumber` | `NInputNumber` |
| `DecimalField` / `FloatField` | `number` | `Decimal` / `float` | `NInputNumber :precision="2"` | 跳过 |
| `BooleanField` | `boolean` | `bool` | `NSwitch` | — |
| `DateField` | `string` | `date` | `NDatePicker type="date"` | — |
| `DatetimeField` | `string` | `datetime` | `NDatePicker type="datetime"` | — |
| `CharEnumField(StatusType)` | `string` | `StatusType` | `NSelect statusTypeOptions` | 同左 |
| `CharEnumField(其他枚举)` | `string` | `str` | `NSelect` + TODO | 同左 |
| `ForeignKeyField` | `number` | `int` | `NSelect` + TODO | 同左 |

## i18n 命名规则

- **模块中文名**：`init` 命令时输入，用于 `route.<module>` 和 `page.<module>` 顶层
- **模型中文名**：类 docstring（`"""仓库"""`）或 `Meta.table_description`
- **字段中文名**：`description="..."`，**截断到第一个中英文句号之前**
  - 例：`description="仓库编号。全局唯一"` → 取 `仓库编号`
  - 例：`description=""` 或未填 → fallback 为字段名本身

## 模块分层与文件职责

CLI 生成后的业务模块严格分层，每层职责不同：

```
app/business/inventory/
├── models.py           # Tortoise 模型 — 只描述表结构
├── schemas.py          # Pydantic — 请求 / 响应 DTO
├── controllers.py      # CRUDBase 实例 — 单资源 CRUD 的入口
├── services.py         # 业务逻辑 — 跨资源编排、事务、缓存
├── init_data.py        # 菜单 / 角色 / 种子数据声明（幂等）
└── api/
    ├── __init__.py     # 汇总子路由
    └── manage.py       # 管理端路由（CRUDRouter + 自定义端点）
```

| 层 | 写什么 | 不写什么 |
|---|---|---|
| `models.py` | 表字段、索引、关系 | 业务校验、默认值逻辑（走 schema / service） |
| `schemas.py` | `XxxCreate` / `XxxUpdate` / `XxxSearch`，字段级校验 | 跨资源逻辑 |
| `controllers.py` | `xxx_controller = CRUDBase(model=Xxx)` | 多模型编排、事务 |
| `services.py` | 事务、跨模型、Redis、审计日志 | HTTP 相关（Request / Response） |
| `api/*.py` | 路由接线、DTO 校验、权限 | 具体业务逻辑（调用 service） |

## CRUD 实践

### 使用 `CRUDRouter` 自动生成 6 条路由

`app/core/router.py` 的 `CRUDRouter` 工厂，一次给每个资源生成：

| 方法 | 路径 | 职责 |
|---|---|---|
| `POST` | `/{prefix}/search` | 分页搜索，body 为 `XxxSearch` |
| `GET` | `/{prefix}/{item_id}` | 取单条 |
| `POST` | `/{prefix}` | 创建 |
| `PATCH` | `/{prefix}/{item_id}` | 更新 |
| `DELETE` | `/{prefix}/{item_id}` | 删除单条 |
| `DELETE` | `/{prefix}` | 批量删除（body: `{ids: [...]}`） |

生成的 `api/manage.py` 大致长这样：

```python
from app.business.inventory.controllers import warehouse_controller
from app.business.inventory.schemas import WarehouseCreate, WarehouseSearch, WarehouseUpdate
from app.utils import CRUDRouter, DependPermission, SearchFieldConfig

warehouse_crud = CRUDRouter(
    prefix="/warehouses",
    controller=warehouse_controller,
    create_schema=WarehouseCreate,
    update_schema=WarehouseUpdate,
    list_schema=WarehouseSearch,
    search_fields=SearchFieldConfig(
        contains_fields=["name", "code"],    # 模糊匹配
        exact_fields=["status"],             # 精确匹配
    ),
    summary_prefix="仓库",
)

router = APIRouter(prefix="/inventory", tags=["inventory"], dependencies=[DependPermission])
router.include_router(warehouse_crud.router)
```

### 覆盖某条标准路由

如果 `list` 需要做 join / 额外字段，用 `@crud.override(...)` 替换生成的路由逻辑：

```python
@warehouse_crud.override("list")
async def _list_warehouses(obj_in: WarehouseSearch):
    q = warehouse_controller.build_search(
        obj_in, contains_fields=["name"], exact_fields=["status"]
    )
    total, items = await warehouse_controller.list(
        page=obj_in.current,
        page_size=obj_in.size,
        search=q,
        order=["-id"],
        prefetch_related=["products"],  # 预加载避免 N+1
    )
    records = [await item.to_dict() for item in items]
    for r, item in zip(records, items):
        r["productCount"] = len(item.products)
    return SuccessExtra(data={"records": records}, total=total, current=obj_in.current, size=obj_in.size)
```

可覆盖的 key：`list` / `get` / `create` / `update` / `remove` / `batch_remove`。

### 新增"集合动作"或"实例动作"端点

标准 CRUD 之外的接口（例如 `POST /warehouses/batch-offline`、`GET /warehouses/{id}/stats`）直接写在 `router` 上，**不要**塞进 `CRUDRouter`：

```python
@router.get("/warehouses/stats", summary="仓库统计")
async def warehouse_stats():
    data = await service_list_warehouse_stats()  # 业务逻辑在 service 层
    return Success(data=data)
```

### 事务与跨表操作放在 `services.py`

需要事务的多步操作，用 `in_transaction`：

```python
from tortoise.transactions import in_transaction
from app.utils import get_db_conn

async def create_product_with_stock(...):
    async with in_transaction(get_db_conn(Product)):
        product = await product_controller.create(obj_in=...)
        await stock_controller.create(obj_in={"product_id": product.id, "qty": 0})
    return product
```

`get_db_conn(Model)` 返回该模型所在连接名，支持[业务模块独立数据库](../ops/database.md)。

### 响应格式

必须用 `app.utils` 提供的三个响应类，**不要**返回裸 dict：

| 类 | 用途 | 典型场景 |
|---|---|---|
| `Success(data=...)` | 单条 / 无分页 | 单条查询、创建、更新 |
| `SuccessExtra(data=..., total=..., current=..., size=...)` | 分页 | 列表 / 搜索 |
| `Fail(code=..., msg=...)` | 业务失败 | 规则不通过、权限不足 |

## 权限与菜单：`init_data.py`

每个业务模块的 `init_data.py` 声明菜单、按钮、角色，启动时幂等执行：

```python
from app.system.services import ensure_menu, ensure_role, reconcile_menu_subtree

INVENTORY_MENU_CHILDREN = [
    {
        "menu_name": "仓库管理",
        "route_name": "inventory_warehouse",
        "route_path": "/inventory/warehouse",
        "component": "view.inventory_warehouse",
        "icon": "mdi:warehouse",
        "order": 1,
        "buttons": [
            {"button_code": "B_INV_CREATE", "button_desc": "创建仓库"},
        ],
    },
]

INVENTORY_ROLE_SEEDS = [
    {
        "role_name": "库存管理员",
        "role_code": "R_INV_MGR",
        "menus": ["home", "inventory", "inventory_warehouse"],
        "buttons": ["B_INV_CREATE"],
        "apis": [
            ("post", "/api/v1/business/inventory/warehouses"),
            ("post", "/api/v1/business/inventory/warehouses/search"),
        ],
    }
]


async def init():
    await ensure_menu(
        menu_name="库存管理",
        route_name="inventory",
        route_path="/inventory",
        icon="mdi:package-variant",
        order=9,
        children=INVENTORY_MENU_CHILDREN,
    )
    # 以 init_data 为单一数据源 —— 启动时清理子树中未声明的菜单 / 按钮
    await reconcile_menu_subtree(
        root_route="inventory",
        declared_route_names={"inventory_warehouse"},
        declared_button_codes={"B_INV_CREATE"},
    )
    for role in INVENTORY_ROLE_SEEDS:
        await ensure_role(**role)
```

**关键约定**：

- `ensure_menu()` / `ensure_role()` **upsert**，反复重启安全
- 调用 `reconcile_menu_subtree()` 后，该子树变成 IaC 模式 — Web UI 手工加的菜单会在下次重启时被清理
- 从 seed 中**删除**一个角色不会自动删数据库中的 `Role` 行（需要走迁移）

详见 [启动初始化与对账](../develop/init-data.md)。

## 删除模块

直接删除 `app/business/<module>/` 整个目录即可，autodiscover 下次启动时自动跳过。

> **注意**：数据库表不会被 tortoise 自动删除。如需清理，手动 `DROP TABLE` 或写一次迁移。

## 相关文档

- [CRUD 基类 API](../develop/crud.md) — `CRUDBase` 方法列表
- [API 路由约定](../develop/api.md) — URL / 方法 / 命名
- [启动初始化与对账](../develop/init-data.md) — 菜单 / 角色 / API 的同步语义
- [切换后端数据库](../ops/database.md) — SQLite / Postgres / MySQL 切换，业务模块独立库
- [命令参考](../reference/commands.md) — 所有 `make` 命令
