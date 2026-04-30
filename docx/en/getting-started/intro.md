# Introduction

[FastSoyAdmin](https://github.com/sleep1223/fast-soy-admin) is a batteries-included full-stack admin template.

- **Frontend** — based on [SoybeanAdmin](https://github.com/soybeanjs/soybean-admin); Vue3 + Vite7 + TypeScript + Pinia + UnoCSS + Naive UI
- **Backend** — FastAPI + Pydantic v2 + Tortoise ORM + Redis; layered as "system + business" with autodiscovered modules

Monorepo layout: `/app` backend, `/web` frontend, `/deploy` Docker / Nginx.

## Highlights

**AI-native**

- **AI-coding friendly** — ships with `CLAUDE.md` + `llms.txt` / `llms-full.md` so Claude Code / Cursor / Copilot get the full architecture, layering rules, API conventions, response codes, and PR checklist up front; agents produce code that matches project conventions out of the box
- **Generators as the AI workbench** — `make cli-gen-all` collapses "add one table" into a single command; the agent only owns `models.py` and override diffs, the rest is emitted by the CLI

**Engineering velocity**

- **End-to-end CLI generation** — `make cli-init / cli-gen-all` turns a Tortoise model into full backend + frontend CRUD (schemas / controllers / api + views / service / typings / i18n)
- **CRUDRouter + `@crud.override`** — the factory emits the 6 standard routes; only override diffs. Aggregate roots stay explicit by design, no abstraction bloat

**Extensible architecture**

- **Autodiscovered business modules** — drop a folder in `app/business/<x>/` and routes / models / init data register themselves; modules are decoupled, cross-module communication goes via the event bus (`emit` / `on`)
- **Multi-database friendly** — modules can declare their own `DB_URL` as `conn_<biz>`; transactions always use `in_transaction(get_db_conn(Model))`
- **Multi-worker startup coordination** — Redis leader lock serializes `init_menus → refresh_api_list → init_data → refresh_cache`, no double reconciliation across K8s replicas

**Security & permissions**

- **Three-tier RBAC + row-level `data_scope`** — menu / API / button checks plus `all / department / self / custom` data scope; button checks live in services, not in UI
- **Menu / role IaC reconciliation** — `ensure_menu` / `reconcile_menu_subtree` / `refresh_api_list` give three explicit semantics so it's clear which subtrees are code-owned vs. user-editable
- **Sqid public IDs** — auto-increment IDs never leak; enumeration-safe

**Contracts & typing**

- **Unified responses** — `{code, msg, data}` + HTTP 200 + camelCase auto-conversion; `BizError` propagates business failures with unique codes
- **End-to-end type safety** — vue-tsc on the frontend, basedpyright (standard) on the backend, both gated in CI
- **Statically checked i18n** — generator output is merged via `import.meta.glob`; `App.I18n.GeneratedPages` lets `vue-tsc` validate every `$t` key

**Observability & resilience**

- **Built-in Radar dashboard** — real-time request / SQL / exception / permission-deny logs
- **fastapi-guard rate limiting + IP banning** — brute-force and scanner traffic blocked automatically
- **Redis cache + graceful fallback** — cached role permissions / constant routes / `token_version` fall back to DB when Redis is down
- **State machine / event bus** — first-class primitives for workflows like tickets, approvals, orders

**Deployment**

- **One-command Docker** — Nginx + FastAPI + Redis pre-wired; `docker compose up -d` and you're live

## How to read these docs

| Goal | Start here |
|---|---|
| Run the project | [Quick start](/en/getting-started/quick-start) |
| Add a business module | [Development guide](/en/getting-started/workflow) |
| Backend architecture / autodiscover / RBAC | [Backend intro](/en/develop/intro) → [Architecture](/en/getting-started/architecture) |
| Frontend routing / requests / theme | [Frontend intro](/en/frontend/intro) |
| Pre-PR conventions | [Backend](/en/standard/backend) · [Vue style](/en/standard/vue) · [Naming](/en/standard/naming) |
| Deploy | [Deployment](/en/ops/deployment) |
| Troubleshoot | [FAQ](/en/faq/) |

## Architecture overview

```
┌─────────────────────────────────────────────────┐
│                  Nginx (:1880)                  │
│      Static assets + /api/* reverse proxy       │
├──────────────────────┬──────────────────────────┤
│   Frontend (:9527)   │   Backend (:9999)        │
│   Vue3 + Vite7       │   FastAPI                │
│                      │                          │
│   Views              │   api/                   │
│     ↓                │     ↓                    │
│   Pinia              │   services/              │
│     ↓                │     ↓                    │
│   Alova ─────────────┼─→ /api/v1/*              │
│                      │     ↓                    │
│                      │   controllers (CRUDBase) │
│                      │     ↓                    │
│                      │   Tortoise / Redis       │
└──────────────────────┴──────────────────────────┘
```

## Resources

- [Live preview](https://fast-soy-admin.sleep0.de/)
- [GitHub](https://github.com/sleep1223/fast-soy-admin)
- [API docs (Apidog)](https://fast-soy-admin.apidog.io)
- [SoybeanAdmin (frontend upstream)](https://github.com/soybeanjs/soybean-admin)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Tortoise ORM](https://tortoise.github.io)
