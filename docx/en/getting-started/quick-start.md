# Quick Start

## Prerequisites

| Tool | Version |
|------|---------|
| Git | — |
| Python | ≥ 3.12 |
| Node.js | ≥ 20.19.0 |
| uv | latest |
| pnpm | ≥ 10.5 |
| just | any |

## Get the code

```bash
git clone https://github.com/sleep1223/fast-soy-admin.git
cd fast-soy-admin
```

## Option A: Docker (recommended)

```bash
just up  # == docker compose up -d
```

Visit `http://localhost:1880`. Services:

- **Nginx** (:1880) — frontend + API reverse-proxy
- **FastAPI** (:9999) — backend API
- **Redis** (:6379) — cache

```bash
just logs      # follow all logs
just logs app  # backend only; `just logs nginx` / `just logs redis` work too; pass a second argument for line count
just down      # stop & remove containers
```

## Option B: Local development

```bash
just install  # install backend + frontend deps
just db-init  # first-time DB init (only once)
just run      # start backend (:9999) and frontend (:9527) together; Ctrl+C to stop both
```

Or run them separately:

```bash
just run backend   # backend only
just run frontend  # frontend only
```

## Default accounts

After `just db-init`, the seed users (password = `123456`):

| User | Roles |
|------|-------|
| `Soybean` | `R_SUPER` |
| `Super` | `R_SUPER` |
| `Admin` | `R_ADMIN` |
| `User` | `R_USER` |

Business demo modules are not loaded by default. The historical HR reference has moved to [Advanced / HR reference](/en/advanced/business-hr).

## What's next

- [Development guide](/en/getting-started/workflow) — end-to-end CRUD module from `just cli-init` to deployable
- [Commands reference](/en/reference/commands) — every `just` target
- [Architecture](/en/getting-started/architecture) — layering, RBAC, lifecycle
- [Response codes](/en/reference/codes) — the unified business code convention

## Project structure

```
fast-soy-admin/
├── app/                  # Backend (FastAPI)
│   ├── __init__.py       # App factory, middleware, lifespan
│   ├── core/             # Framework infrastructure
│   ├── system/           # Built-in modules (auth/users/roles/menus/...)
│   ├── business/         # Business modules (autodiscovered)
│   │   └── hr/           #   reference: employees / departments / tags
│   ├── cli/              # Code generators
│   └── utils/            # Stable import facade for business modules
├── web/                  # Frontend (Vue3 + Vite + NaiveUI)
│   └── src/
│       ├── views/        # Pages
│       ├── service/api/  # API request wrappers
│       ├── typings/api/  # TS types matching backend schemas
│       ├── locales/      # i18n (zh-CN / en-US)
│       ├── router/       # Dynamic router (server-issued)
│       ├── store/        # Pinia
│       └── hooks/        # Composables
├── deploy/               # Docker / Nginx
├── migrations/           # Tortoise migrations
├── tests/                # Backend unit tests
├── justfile              # All common commands
└── docker-compose.yml
```

## Quality checks

```bash
just check  # full backend + frontend gate (run before pushing)
```

Granular:

```bash
just fmt backend         # backend ruff fix + format
just typecheck backend   # backend basedpyright
just test backend        # backend pytest
just lint frontend       # frontend eslint + oxlint
just typecheck frontend  # frontend vue-tsc
just test frontend       # frontend vitest
```
