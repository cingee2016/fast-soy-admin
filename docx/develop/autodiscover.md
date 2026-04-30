# 业务模块自动发现

`app/core/autodiscover.py` 在启动时扫描 `app/business/*/`，按约定加载业务模块的模型、路由、初始化函数与独立 DB 配置。**不需要在任何地方注册业务模块**。

## 触发约定

被识别为"业务模块"的子目录必须满足：

- 直接位于 `app/business/` 下
- 含 `__init__.py`
- 名称不以 `_` 开头（`_internal/`、`__pycache__/` 等会被跳过）

## 模块可以提供的能力

| 文件 | 加载时机 | 行为 |
|---|---|---|
| `models.py` 或 `models/__init__.py` | `Settings` 构造时 | 注册到 `TORTOISE_ORM["apps"]["app_system"].models`（或独立 app） |
| `api/__init__.py` 或 `api.py`（必须导出 `router: APIRouter`） | `create_app()` | `include_router` 到 `/api/v1/business/` |
| `init_data.py`（必须导出 `async def init()`） | `lifespan` 中 leader worker 调用 | 在系统 init 之后、`refresh_all_cache` 之前执行 |
| `config.py`（导出含 `DB_URL` 字段的 Settings 实例） | `Settings` 构造时 | 注册独立 Tortoise 连接 + 独立 app（仅当 `DB_URL` 与主库不同） |

## 标准目录结构

参考 `app/business/hr/`：

```
app/business/<name>/
├── __init__.py
├── config.py          # 可选 — BIZ_SETTINGS（按模块隔离的 Pydantic Settings）
├── ctx.py             # 可选 — 模块上下文变量
├── dependency.py      # 可选 — 模块 FastAPI 依赖
├── models.py          # Tortoise 模型
├── schemas.py         # Pydantic schema
├── controllers.py     # CRUDBase 子类
├── services.py        # 多模型编排、缓存、状态机
├── cache_utils.py     # 可选 — 模块自有缓存失效辅助
├── init_data.py       # async def init()
└── api/
    ├── __init__.py    # 必须导出 router
    ├── manage.py
    ├── dept.py
    └── my.py
```

## 启动加载顺序

```
Settings._build_tortoise_orm()
  ├─ discover_business_models()           # 收集 app.business.*.models
  └─ discover_business_db_configs()       # 找含 DB_URL 的 config.py
       │
       ▼
  TORTOISE_ORM = {
    "connections": {
      "conn_system":  APP_SETTINGS.DB_URL,
      "conn_billing": "postgres://...",   # 仅当业务模块声明独立 DB
    },
    "apps": {
      "app_system":  {"models": [..., "app.business.hr.models", ...], "default_connection": "conn_system"},
      "app_billing": {"models": ["app.business.billing.models"], "default_connection": "conn_billing"},
    },
  }

create_app()
  ├─ register_db(app)                      # 上面那个 TORTOISE_ORM 生效
  ├─ register_routers(app, prefix="/api")  # /api/v1/auth, /api/v1/system-manage/*, ...
  └─ discover_business_routers()           # /api/v1/business/<name>/*

lifespan(app)
  └─ leader 执行 init_data.init() for each business
```

## 常见漂移与排查

### 业务模块被发现但路由不挂

启动日志：

```
Business: module 'inventory' discovered but has no api.py or api/ package — routes will not be registered
```

`app/business/inventory/__init__.py` 存在但没有 `api.py` / `api/__init__.py`。要么补 api，要么在调试期间删掉 `__init__.py` 让模块变成"未启用"。

### `api` 模块不导出 router

```
Business: module 'inventory' api module does not export a valid 'router' (APIRouter) object
```

`api/__init__.py` 必须有：

```python
from .manage import router as manage_router
# ...
router = APIRouter()
router.include_router(manage_router)
```

### 业务模型未参与迁移

启动时**没有**模型注册日志，但接口报 "no such table"。检查：

- `models.py` 文件名是不是叫 `model.py`（漏 `s`）
- 或者用了 `models/` 子包但没有 `__init__.py`

### 业务模块要不要被发现

加 `_` 前缀禁用整个模块（不需要改代码就能临时屏蔽）：

```bash
mv app/business/inventory app/business/_inventory
```

## 业务模块独立数据库

业务模块的 `config.py`：

```python
# app/business/billing/config.py
from pydantic_settings import BaseSettings

class BillingSettings(BaseSettings):
    DB_URL: str = "postgres://billing-host:5432/billing"

    model_config = {"env_file": ".env", "extra": "ignore", "env_prefix": "BILLING_"}

BIZ_SETTINGS = BillingSettings()
```

`discover_business_db_configs` 扫到 `BIZ_SETTINGS.DB_URL`，且与主库 `DB_URL` 不同时，注册独立连接 `conn_billing` + 独立 app `app_billing`。

跨模型事务用 `get_db_conn(Model)` 取连接：

```python
async with in_transaction(get_db_conn(Invoice)):  # 自动选 conn_billing
    await Invoice.create(...)
```

详见 [切换数据库 / 业务模块独立数据库](../ops/database.md#业务模块独立数据库进阶)。

## init_data.init() 执行规则

- 仅 leader worker 执行（多 worker 通过 Redis 锁协调）
- 顺序：按模块名字母排序（`hr` < `inventory` < `notify`）
- 单个模块抛异常**不影响**其他模块——异常被捕获并记录到 `app.state.init_errors`
- 模块内部：`init()` 应当幂等（使用 `ensure_*` 系列）

详见 [启动初始化与对账](./init-data.md)。

## 写在末尾：模块边界

`autodiscover` 是把"业务模块"做成插件的关键。配套的强约定：

- 业务模块**不得反向 import** 其他业务模块（`app.business.crm.*` 不能 `from app.business.hr import ...`）
- 业务模块的 import 入口走 [`app.utils`](../reference/utils.md)
- 跨模块联动通过 [事件总线](./events.md)

违反这些约定时，autodiscover 仍能加载，但"模块自治"的价值会丢失。

## 相关

- [开发指南](../getting-started/workflow.md) — 用 CLI 创建一个新业务模块
- [启动初始化与对账](./init-data.md) — `init()` 怎么执行、怎么对账
- [HR 模块](./business-hr.md) — 标准业务模块的样例
