<!-- markdownlint-disable MD033 MD041 -->

<p align="center">
  <a href="https://github.com/sleep1223/"><img src="web/public/favicon.svg" width="180" height="180" alt="FastSoyAdmin"></a>
</p>

<div align="center">

# FastSoyAdmin

[![license](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![github stars](https://img.shields.io/github/stars/sleep1223/fast-soy-admin)](https://github.com/sleep1223/fast-soy-admin)
![python](https://img.shields.io/badge/python-3.12+-blue?logo=python&logoColor=edb641)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?logo=fastapi&logoColor=edb641)
![Pydantic](https://img.shields.io/badge/Pydantic_v2-e92063?logo=pydantic&logoColor=edb641)
![uv](https://img.shields.io/badge/uv-managed-blueviolet)
[![basedpyright](https://img.shields.io/badge/types-basedpyright-797952.svg?logo=python&logoColor=edb641)](https://github.com/DetachHead/basedpyright)
[![ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

<span>English | <a href="./README.md">中文</a></span>

**A batteries-included full-stack admin template: FastAPI + Vue3**

</div>

## Overview

A batteries-included full-stack admin template — usable as an internal-tools scaffold and as a reference for modern full-stack development.

- **Backend** — FastAPI · Pydantic v2 · Tortoise ORM · Redis
- **Frontend** — Vue3 · Vite8 · TypeScript · Naive UI · UnoCSS · Pinia · Alova · Elegant Router
- **Infra** — Docker Compose (Nginx + FastAPI + Redis), multi-worker startup lock, fastapi-guard, built-in Radar dashboard
- **Code generator** — `cli-init` to scaffold, write `models.py`, `cli-crud` to emit backend + frontend CRUD

## Highlights

- **AI-coding friendly** — ships with [CLAUDE.md](CLAUDE.md) and project conventions
- **One-command CRUD** — Tortoise models generate backend, frontend, types, and i18n
- **Overridable route factory** — `CRUDRouter` for standard APIs, `@crud.override` for custom behavior
- **Modular business apps** — `app/business/<name>/` autodiscovery with event-bus integration
- **Multi-database support** — PostgreSQL / SQLite / MySQL / SQL Server / Oracle
- **RBAC permissions** — menu / API / button checks plus row-level `data_scope`
- **IaC-style bootstrap** — menus, roles, and APIs can be reconciled on startup
- **Unified API contract** — `{code, msg, data}`, camelCase, and Sqid public IDs
- **Full-stack type checks** — basedpyright + vue-tsc + static i18n validation
- **Ops built in** — Radar dashboard, Redis fallback, rate limiting, and IP banning
- **Docker-ready** — Nginx + FastAPI + Redis pre-wired

## Links

- [Live preview](https://fast-soy-admin.sleep0.de/)
- [Documentation](https://sleep1223.github.io/fast-soy-admin-docs/en/)
- [Quick start](https://sleep1223.github.io/fast-soy-admin-docs/en/getting-started/quick-start)
- [Development guide](https://sleep1223.github.io/fast-soy-admin-docs/en/getting-started/workflow)
- [Commands reference](https://sleep1223.github.io/fast-soy-admin-docs/en/reference/commands)
- [Apidog API docs](https://fast-soy-admin.apidog.io)

## Branches

| Branch | Purpose |
| --- | --- |
| `main` | Clean skeleton with no business examples (default) |

## Getting Started

### Requirements

| Tool             | Version |
| ---------------- | ------- |
| Python           | >= 3.12 |
| Node.js          | >= 20.19 |
| uv · pnpm · just | latest  |

### Docker (recommended)

```bash
git clone https://github.com/sleep1223/fast-soy-admin.git
cd fast-soy-admin
just docker-db-init  # first start dependencies and initialize the database
just up              # start the full stack and write default/business seeds
```

Open `http://localhost:1880`.

> Run `initdb` only once for a fresh database; migrations do **not** run automatically. The final app startup writes default users, menus, roles, APIs, and business seed data. See the [deployment guide](https://sleep1223.github.io/fast-soy-admin-docs/en/ops/deployment).

### Local development

```bash
git clone https://github.com/sleep1223/fast-soy-admin.git
cd fast-soy-admin
just install          # uv sync + pnpm install
cp .env.example .env  # copy env template; update SECRET_KEY / DB_URL / REDIS_URL as needed
just db-init          # first-time: create tables + seed
just run              # backend (:9999) + frontend (:9527) in parallel, Ctrl+C stops both
```

## Common Commands

All commands are wrapped in `justfile`. Run `just --list` for the full list.

| Command                                | Purpose                                               |
| -------------------------------------- | ----------------------------------------------------- |
| `just install`                         | Install backend + frontend dependencies               |
| `just run`                             | Run backend + frontend dev servers together           |
| `just run backend` / `just run frontend` | Run backend / frontend only                         |
| `just check`                           | Run all backend + frontend quality gates (pre-commit) |
| `just check backend` / `just check frontend` | Check backend / frontend only                  |
| `just mm`                              | `makemigrations` + `migrate`                          |
| `just cli-init xxx`                | Scaffold a new business module                        |
| `just cli-gen xxx`                 | Choose models and fuzzy/exact search fields; generate backend code |
| `just cli-gen-web xxx name`     | Choose models and list/search fields; generate frontend code |
| `just cli-gen-all xxx name`     | Choose and generate both at once                      |
| `just cli-crud xxx name`        | Alias for full CRUD generation                        |
| `just up` / `just down` / `just logs`  | Docker lifecycle                                      |

See the [commands reference](https://sleep1223.github.io/fast-soy-admin-docs/en/reference/commands) for the complete list.

## Adding a new business module

```bash
just cli-init inventory                   # 1. scaffold the module
$EDITOR app/business/inventory/models.py  # 2. define Tortoise models
just cli-crud inventory Inventory         # 3. generate backend + frontend CRUD (i18n auto-merged)
just mm                                   # 4. run migrations
just run                                  # 5. verify
just check                                # 6. pre-commit
```

Walkthrough and field type mappings: [Development guide](https://sleep1223.github.io/fast-soy-admin-docs/en/getting-started/workflow).

## Architecture

```
app/
├── core/           # Framework infra (CRUDBase / CRUDRouter / Schema / auth / cache / events / Sqids)
├── system/         # System modules (auth / user / role / menu / api / dictionary / radar)
├── business/       # Business modules (autodiscovered)
├── cli/            # Code generator
└── utils/          # Unified re-export surface for business modules
web/src/
├── views/          # Pages (Elegant Router source)
├── service/api/    # Alova HTTP wrappers
├── typings/api/    # TS types
├── store/modules/  # Pinia
├── router/         # Elegant Router + guards
└── locales/        # vue-i18n
```

Layers: `api/` → `services/` → `controllers/` → `models + schemas`. Business modules **must not** reverse-import `app.system.*` (except a few explicitly exposed services) and **must not** import sibling modules — cross-module talk uses the event bus. See [architecture](https://sleep1223.github.io/fast-soy-admin-docs/en/getting-started/architecture).

## Switching databases

Change `DB_URL` in `.env` and run `just db-init`. PostgreSQL / SQLite / MySQL / SQL Server / Oracle are supported.

PostgreSQL (`tortoise-orm[asyncpg]`) and SQLite (`aiosqlite`, ships with tortoise-orm) are bundled by default; install extras for other engines:

```bash
uv sync --extra mysql   # MySQL (asyncmy)
uv sync --extra mssql   # SQL Server (asyncodbc)
uv sync --extra oracle  # Oracle (asyncodbc)
```

A module can declare its own `DB_URL` in `config.py`; autodiscover registers it as `conn_<biz>`. For cross-model transactions, use `get_db_conn(Model)` to pick the connection. See [switch database](https://sleep1223.github.io/fast-soy-admin-docs/en/ops/database).

## Response Codes

All endpoints return `{"code": "xxxx", "msg": "...", "data": ...}` with HTTP status always 200.

| Range       | Meaning                                  | Typical frontend behavior           |
| ----------- | ---------------------------------------- | ----------------------------------- |
| `0000`      | Success                                  | Normal processing                   |
| `1xxx`      | Internal / serialization error           | Auto-toasted by the framework       |
| `21xx`      | Auth failure (token / session)           | Logout / modal / auto token refresh |
| `22xx`      | Authorization failure (RBAC / button)    | Show error toast                    |
| `23xx`      | Resource conflict (unique constraint)    | Show error toast                    |
| `24xx`      | Generic business failure                 | Show error toast                    |
| `25xx`      | Rate-limit / security                    | Show error toast                    |
| `26xx`      | Schema required-field fallback           | Show error toast                    |
| `4000–9999` | User-defined (modules start at `4000`)   | Handled by callers                  |

See [response codes](https://sleep1223.github.io/fast-soy-admin-docs/en/reference/codes).

## Frontend sync

`web/` is maintained in a separate repo, [fast-soy-admin-frontend](https://github.com/sleep1223/fast-soy-admin-frontend), with **no common ancestor**. Upstream sync is a manual `git subtree` workflow — see commits prefixed `chore(web): sync with fast-soy-admin-frontend@...`.

## Screenshots

![Home - Chinese](https://sleep1223.github.io/fast-soy-admin-docs/screenshots/home-zh.png)
![Home - English](https://sleep1223.github.io/fast-soy-admin-docs/screenshots/home-en.png)
![Radar - Dashboard](https://sleep1223.github.io/fast-soy-admin-docs/screenshots/radar-dashboard.png)
![Radar - Requests](https://sleep1223.github.io/fast-soy-admin-docs/screenshots/radar-requests.png)
![Radar - SQL](https://sleep1223.github.io/fast-soy-admin-docs/screenshots/radar-sql.png)
![Radar - Exceptions](https://sleep1223.github.io/fast-soy-admin-docs/screenshots/radar-exceptions.png)

## TODO

- [x] Redis caching
- [x] One-command Docker deploy
- [x] CLI code generator (backend + frontend)
- [x] Built-in Radar dashboard (requests / SQL / exceptions / audit)
- [x] `main` clean branch
- [ ] End-to-end tests

## Contributing

[Pull requests](https://github.com/sleep1223/fast-soy-admin/pulls) and [issues](https://github.com/sleep1223/fast-soy-admin/issues/new) welcome.

<a href="https://github.com/sleep1223/fast-soy-admin/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=sleep1223/fast-soy-admin" />
</a>

## License

[MIT © 2024](./LICENSE)
