# Commands Reference

A root `Makefile` wraps all common operations. Run `make` (or `make help`) for the full list.

> `MOD=xxx` denotes a positional argument: e.g. `make cli-init MOD=inventory`.

## Backend

| Raw | Make | Purpose |
|---|---|---|
| `uv sync` | `make install` | Install backend deps |
| `uv run python run.py` | `make run` | Start backend dev server (:9999) |
| `uv run ruff check app/`<br>`uv run ruff format --check app/` | `make lint` | Ruff lint (no fix) |
| `uv run ruff check --fix app/`<br>`uv run ruff format app/` | `make fmt` | Ruff fix + format |
| `uv run basedpyright app` | `make typecheck` | Static type check |
| `uv run pytest tests/ -v` | `make test` | Unit tests |
| — | `make check` | fmt + typecheck + test |

## Database

| Raw | Make | Purpose |
|---|---|---|
| `uv run python -m app.cli initdb` | `make initdb` | First-time DB init (tables + base data) |
| `uv run tortoise makemigrations` | `make makemigrations` | Generate migration files from model changes |
| `uv run tortoise migrate` | `make migrate` | Apply pending migrations |
| — | `make mm` | makemigrations + migrate in one go |
| `uv run tortoise history` | `make dbhistory` | Migration history |

## CLI code generation

| Raw | Make | Purpose |
|---|---|---|
| `uv run python -m app.cli init <MOD>` | `make cli-init MOD=xxx` | Create module skeleton (`models.py` only) |
| `uv run python -m app.cli gen <MOD>` | `make cli-gen MOD=xxx` | Parse `models.py`, generate backend schemas/controllers/api |
| `uv run python -m app.cli gen-web <MOD>` | `make cli-gen-web MOD=xxx [CN=Chinese-Name]` | Parse `models.py`, generate frontend service/typings/views/i18n fragments |
| — | `make cli-gen-all MOD=xxx [CN=Chinese-Name]` | Run `cli-gen` + `cli-gen-web` |

For details see [Development guide](/en/getting-started/workflow).

## Frontend

| Raw | Make | Purpose |
|---|---|---|
| `cd web && pnpm install` | `make web-install` | Install frontend deps |
| `cd web && pnpm dev` | `make web-dev` | Frontend dev server (:9527) |
| `cd web && pnpm build` | `make web-build` | Production build |
| `cd web && pnpm lint` | `make web-lint` | ESLint + oxlint |
| `cd web && pnpm typecheck` | `make web-typecheck` | vue-tsc |
| — | `make web-check` | web-lint + web-typecheck |

## Full stack

| Command | Purpose |
|---|---|
| `make install-all` | Install backend + frontend deps |
| `make dev` | Run backend (:9999) + frontend (:9527) together; Ctrl+C stops both |
| `make check-all` | Run all backend + frontend quality checks |

## Docker

| Raw | Make | Purpose |
|---|---|---|
| `docker compose up -d` | `make up` | Start full stack (nginx :1880 + fastapi :9999 + redis) |
| `docker compose up -d --build` | `make rebuild` | Rebuild images and recreate containers (after code / Dockerfile changes) |
| `docker compose down` | `make down` | Stop & remove containers |
| `docker compose logs -f` | `make logs` | Tail all logs; pass `SVC=app\|nginx\|redis` to filter, `TAIL=N` for line count |

## Typical workflow

```bash
# 1. install (first time)
make install-all

# 2. init DB (first time)
make initdb

# 3. create module skeleton
make cli-init MOD=inventory

# 4. edit app/business/inventory/models.py — define Tortoise models

# 5. generate backend code
make cli-gen MOD=inventory

# 6. generate frontend code
make cli-gen-web MOD=inventory CN=Inventory

# 5+6 in one shot:
# make cli-gen-all MOD=inventory CN=Inventory

# 7. run migrations
make mm

# 8. start dev servers
make dev

# 9. pre-push gate
make check-all
```
