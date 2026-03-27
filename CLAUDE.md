# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FastSoyAdmin is a full-stack admin template with a **FastAPI** backend (Python) and **Vue3** frontend (TypeScript). The repo is a monorepo: backend lives at root (`/app`), frontend in `/web` (pnpm workspaces).

## Common Commands

### Backend

```bash
# Install dependencies (uses uv or pdm)
uv sync                       # or: pdm install
# Run dev server (port 9999)
python run.py
# Lint & format
ruff check app/               # lint
ruff format app/               # format
# Type check
pyright app/
```

### Frontend

```bash
cd web
pnpm install                  # install dependencies
pnpm dev                      # dev server (port 9527)
pnpm build                    # production build
pnpm lint                     # eslint
pnpm typecheck                # vue-tsc type check
```

### Docker

```bash
docker compose up -d          # full stack: nginx(:1880) + fastapi + redis
```

## Architecture

### Backend (`/app`)

Layered architecture: **Router → Controller → CRUD/Model**

- `app/__init__.py` — App factory, middleware registration, startup hooks
- `app/api/v1/` — FastAPI routers grouped by domain (auth, route, system_manage)
- `app/controllers/` — Business logic layer (user, role, menu, api, log)
- `app/models/system/admin.py` — All ORM models (Tortoise ORM): User, Role, Menu, Api, Button, Log, APILog
- `app/schemas/` — Pydantic request/response schemas with camelCase aliases for frontend compatibility
- `app/core/`:
  - `init_app.py` — DB registration (Tortoise + Aerich), exception handlers, router mounting
  - `dependency.py` — `AuthControl` (JWT auth) and `PermissionControl` (RBAC) as FastAPI dependencies
  - `crud.py` — Generic CRUD base class used by all controllers
  - `middlewares.py` — Request logging, background task middleware
  - `ctx.py` — Context variables (user_id, request_id)
- `app/settings/config.py` — Pydantic Settings loaded from `.env`
- `app/utils/security.py` — Password hashing (argon2), JWT token creation

**Key patterns:**

- RBAC: Users ↔ Roles ↔ (Menus, APIs, Buttons) — all many-to-many
- Super admin role `R_SUPER` bypasses permission checks
- Standard response format: `{"code": "0000", "msg": "OK", "data": {...}}`
- JWT auth: access token (12h) + refresh token (7d), HS256
- API routes auto-registered to DB on startup for permission management

### Frontend (`/web`)

Vue3 + Vite + Naive UI + Elegant Router + Pinia

- `web/src/views/` — Page components
- `web/src/service/` — API service calls
- `web/src/store/` — Pinia stores
- `web/src/router/` — Elegant Router config (generates routes from file structure)
- `web/src/locales/` — i18n translations
- `web/packages/` — Internal monorepo packages (alova HTTP client, axios, hooks, utils, color, uno-preset)

### Database

- Default: SQLite (`app_system.sqlite3`)
- ORM: Tortoise ORM
- Migrations: Aerich
- Caching: Redis via fastapi-cache2

## Gate Checks

After modifying code, run the corresponding checks before finishing:

### Backend
```bash
ruff check app/               # lint
ruff format app/               # format
pyright app                    # type check
pytest tests/ -v               # tests
```

### Frontend
```bash
cd web
pnpm lint                     # eslint
pnpm typecheck                # vue-tsc type check
```

## Configuration

- `.env` — SECRET_KEY, DEBUG, CORS settings, Redis URL, DB path
- `ruff.toml` — Line length 200, rules E/F/I, double quotes
- Pyright strict mode on `app/` directory

## Deployment

Nginx serves the built frontend and proxies `/api/*` to the FastAPI backend (port 9999). Redis provides caching. All orchestrated via `docker-compose.yml` with configs in `/deploy/`.
