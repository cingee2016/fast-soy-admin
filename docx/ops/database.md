# 切换后端数据库

FastSoyAdmin 的 ORM 层用 [Tortoise ORM](https://tortoise.github.io)，原生支持 **PostgreSQL / SQLite / MySQL(MariaDB) / SQL Server** 四种引擎。**切换数据库只需改一个环境变量 `DB_URL`，不需要动代码**。

## 快速切换（单数据库）

在项目根目录的 `.env` 里改 `DB_URL`：

```dotenv
# PostgreSQL（默认，驱动 asyncpg）
DB_URL="postgres://postgres:password@localhost:5432/fastsoyadmin"

# SQLite（开发/单机，aiosqlite 由 tortoise-orm 自带）
DB_URL="sqlite://app_system.sqlite3?busy_timeout=5000"

# MySQL / MariaDB
DB_URL="mysql://root:password@localhost:3306/fastsoyadmin"

# SQL Server
DB_URL="mssql://sa:Password123@localhost:1433/fastsoyadmin?driver=ODBC%20Driver%2018%20for%20SQL%20Server&encrypt=no&trust_server_certificate=yes"
```

切换完成后执行一次首次初始化：

```bash
make initdb         # 等同 tortoise init-db + 首次种子数据
```

后续模型变更照旧：

```bash
make mm             # makemigrations + migrate
```

## URL 语法速查

| 引擎 | URL 示例 | 说明 |
|---|---|---|
| SQLite（相对路径） | `sqlite://app_system.sqlite3?busy_timeout=5000` | **两个斜杠**，相对项目根 |
| SQLite（绝对路径） | `sqlite:///var/data/db.sqlite3?journal_mode=WAL` | **三个斜杠**，后接绝对路径 |
| PostgreSQL | `postgres://user:pwd@host:5432/db` | 默认 asyncpg；也可 `asyncpg://...` / `psycopg://...` 显式指定 |
| MySQL | `mysql://user:pwd@host:3306/db` | 需额外安装 `aiomysql` 或 `asyncmy` |
| SQL Server | `mssql://sa:pwd@host:1433/db?driver=ODBC...` | 需要 ODBC 驱动；`encrypt` / `trust_server_certificate` 视情况配置 |

完整 URL 语法参考 [Tortoise ORM 官方文档](https://tortoise.github.io/setup.html#db-url)。

## 驱动安装

`pyproject.toml` 默认依赖 PostgreSQL 驱动（`tortoise-orm[asyncpg]`），SQLite 驱动 `aiosqlite` 是 tortoise-orm 的核心依赖（开箱即用）；其他引擎通过 optional extras 选装：

```toml
dependencies = [
  "tortoise-orm[asyncpg]>=1.1.7",   # PostgreSQL（默认）+ SQLite（aiosqlite, tortoise 自带）
  ...
]

[project.optional-dependencies]
mysql = ["tortoise-orm[asyncmy]>=1.1.7"]
mssql = ["tortoise-orm[asyncodbc]>=1.1.7"]
oracle = ["tortoise-orm[asyncodbc]>=1.1.7"]
```

切换到 MySQL / MSSQL / Oracle 时安装对应 extra：

::: code-group
```bash [MySQL / MariaDB]
uv sync --extra mysql       # asyncmy
```

```bash [SQL Server]
uv sync --extra mssql       # asyncodbc，另需 OS 层安装 ODBC Driver 18
```

```bash [Oracle]
uv sync --extra oracle      # asyncodbc
```
:::

需要同时装多个时叠加 `--extra`，例如 `uv sync --extra mysql --extra mssql`。

## 容器部署切换

`.env.docker` 示例（Postgres）：

```dotenv
DB_URL="postgres://postgres:postgres@db:5432/fastsoyadmin"
```

同时在 `docker-compose.yml` 的 `db` 服务下放一份 Postgres 容器即可；示例参考 `deploy/` 目录。

## 业务模块独立数据库（进阶）

有时候某些业务模块需要使用**另一个数据库**（例如账务模块用独立的 OLAP 库）。FastSoyAdmin 的 autodiscover 机制支持自动把这类模块注册为独立连接。

### 声明方式

在业务模块的 `config.py` 中声明 `DB_URL`：

```python
# app/business/billing/config.py
from pydantic_settings import BaseSettings


class BillingSettings(BaseSettings):
    DB_URL: str = "postgres://user:pwd@billing-host:5432/billing"

    model_config = {"env_file": ".env", "extra": "ignore", "env_prefix": "BILLING_"}


BIZ_SETTINGS = BillingSettings()
```

对应在 `.env` 中可用 `BILLING_DB_URL=...` 覆盖。

### 发生了什么

启动时 `app/core/autodiscover.py` 的 `discover_business_db_configs()`：

1. 扫描 `app/business/*/config.py`
2. 提取其中任何带 `DB_URL` 属性的对象
3. 如果该值**不同于**主库 `DB_URL`，就在 `TORTOISE_ORM` 里注册一条新连接 `conn_billing` 并把这个模块的模型挂到新 app `billing` 下
4. 如果该值**等于**主库，就合并到默认连接（无副作用）

### 使用事务时选对连接

跨模块的事务必须指定正确的连接名：

```python
from tortoise.transactions import in_transaction
from app.utils import get_db_conn
from app.business.billing.models import Invoice

async with in_transaction(get_db_conn(Invoice)):
    await Invoice.create(...)
```

`get_db_conn(Model)` 自动返回该模型所在的连接名（`conn_system` 或 `conn_billing`），不需要硬编码。

### 独立库也要单独迁移

每个连接对应一个独立的迁移目录：

```
migrations/
├── app_system/          # 主库（系统 + 共用主库的业务模块）
└── billing/             # billing 模块独立库
```

`make makemigrations` 会为每个 app 生成对应目录。

## 常见坑位

### 1. 连接池大小

默认 Tortoise / asyncpg 池较小，生产高并发场景建议在 URL 里配：

```
postgres://user:pwd@host:5432/db?maxsize=50&minsize=5
```

### 2. SQLite 并发写

SQLite 默认单写，推荐开启 WAL：

```
sqlite:///data/app.sqlite3?journal_mode=WAL&busy_timeout=5000
```

### 3. MySQL 时间戳精度

若需要毫秒级时间戳，MySQL 5.7+ 需用 `DATETIME(3)`。Tortoise 默认使用 `DATETIME` 无小数位，可在模型里加 `auto_now=True` 交由应用层处理。

### 4. 时区

Tortoise 由 `TORTOISE_ORM` 里的 `use_tz` 和 `timezone` 控制。项目默认 `use_tz=false, timezone=Asia/Shanghai`。PostgreSQL 建议 `use_tz=true` 并统一存 UTC，避免夏令时问题。

## 相关

- [配置](./config.md) — 所有 `.env` 配置项
- [开发指南](../getting-started/workflow.md) — 新增业务模块流程
- [启动初始化](../develop/init-data.md) — 迁移与首次数据装载的关系
