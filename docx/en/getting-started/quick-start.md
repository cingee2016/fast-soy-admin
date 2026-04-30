# Quick Start

## Prerequisites

| Tool | Version |
|------|---------|
| Git | — |
| Python | ≥ 3.12 |
| Node.js | ≥ 20.0.0 |
| uv | latest |
| pnpm | ≥ 10.5 |
| make | any |

## Get the code

```bash
git clone https://github.com/sleep1223/fast-soy-admin.git
cd fast-soy-admin
```

## Option A: Docker (recommended)

```bash
make up           # == docker compose up -d
```

Visit `http://localhost:1880`. Services:

- **Nginx** (:1880) — frontend + API reverse-proxy
- **FastAPI** (:9999) — backend API
- **Redis** (:6379) — cache

```bash
make logs                  # follow all logs
make logs SVC=app          # backend only; SVC=nginx|redis works too, TAIL=N for line count
make down                  # stop & remove containers
```

## Option B: Local development

```bash
make install-all  # install backend + frontend deps
make initdb       # first-time DB init (only once)
make dev          # start backend (:9999) and frontend (:9527) together; Ctrl+C to stop both
```

Or run them separately:

```bash
make run          # backend only
make web-dev      # frontend only
```

## Default accounts

After `make initdb`, the seed users (password = `123456`):

| User | Roles |
|------|-------|
| `Soybean` | `R_SUPER` |
| `Super` | `R_SUPER` |
| `Admin` | `R_ADMIN` |
| `User` | `R_USER` |

The HR demo (auto-loaded by `app/business/hr/init_data.py`) adds 9 more accounts (`9001`–`9009`, password `123456`) including 5 department managers; see [HR module](/en/develop/business-hr) for the full matrix.

## What's next

- [Development guide](/en/getting-started/workflow) — end-to-end CRUD module from `make cli-init` to deployable
- [Commands reference](/en/reference/commands) — every `make` target
- [Architecture](/en/getting-started/architecture) — layering, RBAC, lifecycle
- [Response codes](/en/reference/codes) — the unified business code convention

## Project structure

```
fast-soy-admin/
├── app/                          # Backend (FastAPI)
│   ├── __init__.py               # App factory, middleware, lifespan
│   ├── core/                     # Framework infrastructure
│   ├── system/                   # Built-in modules (auth/users/roles/menus/...)
│   ├── business/                 # Business modules (autodiscovered)
│   │   └── hr/                   #   reference: employees / departments / tags
│   ├── cli/                      # Code generators
│   └── utils/                    # Stable import facade for business modules
├── web/                          # Frontend (Vue3 + Vite + NaiveUI)
│   └── src/
│       ├── views/                # Pages
│       ├── service/api/          # API request wrappers
│       ├── typings/api/          # TS types matching backend schemas
│       ├── locales/              # i18n (zh-CN / en-US)
│       ├── router/               # Dynamic router (server-issued)
│       ├── store/                # Pinia
│       └── hooks/                # Composables
├── deploy/                       # Docker / Nginx
├── migrations/                   # Tortoise migrations
├── tests/                        # Backend unit tests
├── Makefile                      # All common commands
└── docker-compose.yml
```

## Quality checks

```bash
make check-all    # full backend + frontend gate (run before pushing)
```

Granular:

```bash
make fmt          # backend ruff fix + format
make typecheck    # backend basedpyright
make test         # backend pytest
make web-lint     # frontend eslint + oxlint
make web-typecheck # frontend vue-tsc
```
