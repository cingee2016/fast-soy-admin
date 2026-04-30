# Switching the database

FastSoyAdmin uses [Tortoise ORM](https://tortoise.github.io), with native support for **PostgreSQL / SQLite / MySQL (MariaDB) / SQL Server**. **Switching DB only requires changing `DB_URL` in `.env`; no code changes**.

## Quick switch (single DB)

Edit `.env`:

```dotenv
# PostgreSQL (default, driver: asyncpg)
DB_URL="postgres://postgres:password@localhost:5432/fastsoyadmin"

# SQLite (dev/single-node, aiosqlite ships with tortoise-orm)
DB_URL="sqlite://app_system.sqlite3?busy_timeout=5000"

# MySQL / MariaDB
DB_URL="mysql://root:password@localhost:3306/fastsoyadmin"

# SQL Server
DB_URL="mssql://sa:Password123@localhost:1433/fastsoyadmin?driver=ODBC%20Driver%2018%20for%20SQL%20Server&encrypt=no&trust_server_certificate=yes"
```

Then init once:

```bash
make initdb         # = tortoise init-db + first-time seeds
```

Subsequent model changes:

```bash
make mm             # makemigrations + migrate
```

## URL syntax cheat sheet

| Engine | URL example | Notes |
|---|---|---|
| SQLite (relative) | `sqlite://app_system.sqlite3?busy_timeout=5000` | **two** slashes, relative to project root |
| SQLite (absolute) | `sqlite:///var/data/db.sqlite3?journal_mode=WAL` | **three** slashes, then absolute path |
| PostgreSQL | `postgres://user:pwd@host:5432/db` | default asyncpg; `asyncpg://...` / `psycopg://...` to specify |
| MySQL | `mysql://user:pwd@host:3306/db` | requires `aiomysql` or `asyncmy` |
| SQL Server | `mssql://sa:pwd@host:1433/db?driver=ODBC...` | requires ODBC driver; tweak `encrypt` / `trust_server_certificate` as needed |

Full URL syntax: [Tortoise ORM docs](https://tortoise.github.io/setup.html#db-url).

## Driver install

PostgreSQL is bundled by default (`tortoise-orm[asyncpg]`); SQLite also works out of the box via Tortoise's built-in `aiosqlite`. Other engines are shipped as optional extras in `pyproject.toml`:

```toml
dependencies = [
  "tortoise-orm[asyncpg]>=1.1.7",   # PostgreSQL (default) + SQLite (aiosqlite, bundled with tortoise)
  ...
]

[project.optional-dependencies]
mysql = ["tortoise-orm[asyncmy]>=1.1.7"]
mssql = ["tortoise-orm[asyncodbc]>=1.1.7"]
oracle = ["tortoise-orm[asyncodbc]>=1.1.7"]
```

Install the matching extra for MySQL / MSSQL / Oracle:

::: code-group
```bash [MySQL / MariaDB]
uv sync --extra mysql       # asyncmy
```

```bash [SQL Server]
uv sync --extra mssql       # asyncodbc, also needs OS-level ODBC Driver 18
```

```bash [Oracle]
uv sync --extra oracle      # asyncodbc
```
:::

Stack multiple `--extra` flags if you need more than one, e.g. `uv sync --extra mysql --extra mssql`.

## Container deployment

`.env.docker` example (Postgres):

```dotenv
DB_URL="postgres://postgres:postgres@db:5432/fastsoyadmin"
```

Add a Postgres container under `db` in `docker-compose.yml`; sample in `deploy/`.

## Business module standalone database (advanced)

A business module may need a **separate database** (e.g. an OLAP DB for billing). Autodiscover supports this.

### Declaration

In the module's `config.py`:

```python
# app/business/billing/config.py
from pydantic_settings import BaseSettings


class BillingSettings(BaseSettings):
    DB_URL: str = "postgres://user:pwd@billing-host:5432/billing"

    model_config = {"env_file": ".env", "extra": "ignore", "env_prefix": "BILLING_"}


BIZ_SETTINGS = BillingSettings()
```

`.env` can override with `BILLING_DB_URL=...`.

### What happens

`app/core/autodiscover.py`'s `discover_business_db_configs()` at startup:

1. Scans `app/business/*/config.py`
2. Extracts any object with a `DB_URL` attribute
3. If the value **differs** from the main `DB_URL`, registers a new connection `conn_billing` and mounts the module's models under `app_billing`
4. If the value **equals** the main one, merges into the default connection (no side effect)

### Use the right connection in transactions

```python
from tortoise.transactions import in_transaction
from app.utils import get_db_conn
from app.business.billing.models import Invoice

async with in_transaction(get_db_conn(Invoice)):
    await Invoice.create(...)
```

`get_db_conn(Model)` returns the correct connection name (`conn_system` or `conn_billing`); never hard-code.

### Standalone DB needs its own migrations

Each connection has its own migration folder:

```
migrations/
├── app_system/          # main (system + business sharing main)
└── billing/             # standalone billing DB
```

`make makemigrations` generates per-app folders.

## Common pitfalls

### 1. Connection pool size

Production high-concurrency: tune in URL:

```
postgres://user:pwd@host:5432/db?maxsize=50&minsize=5
```

### 2. SQLite concurrent writes

SQLite is single-writer by default; enable WAL:

```
sqlite:///data/app.sqlite3?journal_mode=WAL&busy_timeout=5000
```

### 3. MySQL timestamp precision

Need millisecond precision on MySQL 5.7+? Use `DATETIME(3)`. Tortoise's default is plain `DATETIME` without fractional seconds; if needed, set `auto_now=True` and let app-level handle it.

### 4. Timezone

Tortoise's `use_tz` and `timezone` are in `TORTOISE_ORM`. Defaults: `use_tz=false, timezone=Asia/Shanghai`. For PostgreSQL, prefer `use_tz=true` storing UTC to avoid DST issues.

## See also

- [Configuration](/en/ops/config) — all `.env`
- [Development guide](/en/getting-started/workflow) — adding business modules
- [Startup init](/en/develop/init-data) — relation to migration & first-time seeds
