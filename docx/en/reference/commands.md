# Commands Reference

A root `justfile` wraps all common operations. Run `just` (or `just --list`) for the full list.

> `xxx` denotes a positional argument, e.g. `just cli-init inventory`.

## Backend

| Raw | just | Purpose |
|---|---|---|
| `uv sync` | `just install backend` | Install backend deps |
| `uv run python run.py` | `just run backend` | Start backend dev server (:9999) |
| `uv run ruff check app/`<br>`uv run ruff format --check app/` | `just lint backend` | Ruff lint (no fix) |
| `uv run ruff check --fix app/`<br>`uv run ruff format app/` | `just fmt backend` | Ruff fix + format |
| `uv run basedpyright app` | `just typecheck backend` | Static type check |
| `uv run pytest tests/ -v` | `just test backend` | Unit tests |
| — | `just check backend` | fmt + typecheck + test |

## Database

| Raw | just | Purpose |
|---|---|---|
| `uv run python -m app.cli initdb` | `just db-init` | First-time DB init (tables + base data) |
| `uv run python -m app.cli initdb --force` | `just db-reset` | Reset the current dev database and local migration baseline, then initialize again |
| `uv run tortoise makemigrations` | `just makemigrations` | Generate migration files from model changes |
| `uv run tortoise migrate` | `just migrate` | Apply pending migrations |
| — | `just mm` | makemigrations + migrate in one go |
| `uv run tortoise history` | `just dbhistory` | Migration history |

## CLI code generation

| Raw | just | Purpose |
|---|---|---|
| `uv run python -m app.cli init <MOD>` | `just cli-init xxx` | Create module skeleton (`models.py` only) |
| `uv run python -m app.cli gen <MOD>` | `just cli-gen xxx` | Parse `models.py`, generate backend schemas/controllers/api |
| `uv run python -m app.cli gen-web <MOD>` | `just cli-gen-web xxx [Chinese-Name]` | Parse `models.py`, generate frontend service/typings/views/i18n fragments |
| — | `just cli-gen-all xxx [Chinese-Name]` | Run `cli-gen` + `cli-gen-web` |

For details see [Development guide](/en/getting-started/workflow).

## Frontend

| Raw | just | Purpose |
|---|---|---|
| `cd web && pnpm install` | `just install frontend` | Install frontend deps |
| `cd web && pnpm dev` | `just run frontend` | Frontend dev server (:9527) |
| `cd web && pnpm exec oxlint`<br>`cd web && pnpm exec eslint .` | `just lint frontend` | Frontend lint (no fix) |
| `cd web && pnpm lint`<br>`cd web && pnpm fmt` | `just fmt frontend` | Frontend fix + format |
| `cd web && pnpm typecheck` | `just typecheck frontend` | vue-tsc |
| `cd web && pnpm test` | `just test frontend` | Vitest unit tests |
| `cd web && pnpm build` | `just build frontend` / `just build` | Production build |
| — | `just check frontend` | fmt + typecheck + test |

## Full stack

| Command | Purpose |
|---|---|
| `just install` | Install backend + frontend deps |
| `just run` | Run backend (:9999) + frontend (:9527) together; Ctrl+C stops both |
| `just fmt` | Format / fix backend + frontend code |
| `just test` | Run backend + frontend tests |
| `just check` | Run all backend + frontend quality checks |

Compatibility aliases are still available: `just install-all`, `just check-all`, `just web-install`, `just web-dev`, `just web-build`, `just web-lint`, `just web-typecheck`, `just web-check`.

## Docker

| Raw | just | Purpose |
|---|---|---|
| `docker compose up -d` | `just up` | Start full stack (nginx :1880 + fastapi :9999 + redis) |
| `docker compose up -d --build` | `just rebuild` | Rebuild images and recreate containers (after code / Dockerfile changes) |
| `docker compose down` | `just down` | Stop & remove containers |
| `docker compose logs -f` | `just logs` | Tail all logs; use `just logs app` to filter by service, `just logs app 200` to set line count |

## Typical workflow

```bash
# 1. install (first time)
just install

# 2. init DB (first time)
just db-init

# 3. create module skeleton
just cli-init inventory

# 4. edit app/business/inventory/models.py — define Tortoise models

# 5. generate backend code
just cli-gen inventory

# 6. generate frontend code
just cli-gen-web inventory Inventory

# 5+6 in one shot:
# just cli-gen-all inventory Inventory

# 7. run migrations
just mm

# 8. start dev servers
just run

# 9. pre-push gate
just check
```
