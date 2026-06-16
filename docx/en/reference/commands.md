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
| `uv run python -m app.cli gen <MOD>` | `just cli-gen xxx` | Choose CRUD models plus fuzzy/exact search fields; generate backend schemas/controllers/api |
| `uv run python -m app.cli gen-web <MOD>` | `just cli-gen-web xxx [Chinese-Name]` | Choose page models plus list/search fields; generate frontend service/typings/views/i18n |
| `uv run python -m app.cli gen-all <MOD>` | `just cli-gen-all xxx [Chinese-Name]` | Choose and generate backend + frontend CRUD in one command |
| `uv run python -m app.cli crud <MOD>` | `just cli-crud xxx [Chinese-Name]` | Alias for full CRUD generation |

### Parameterized generation (AI friendly)

All generator commands support `-h/--help`. Add `--yes` to generate without prompts:

```bash
uv run python -m app.cli crud utility_fee --cn-name "Utility Fees" --yes --force
```

Add `--dry-run` before generation to preview which files would be created, overwritten, or appended. Dry-run does not write to disk and does not require a clean Git worktree:

```bash
just cli-crud inventory Inventory "--yes --dry-run"
```

Model and field specs use the same `Model:field1,field2` shape. Repeat an option or separate specs with semicolons for multiple models:

```bash
uv run python -m app.cli crud utility_fee \
  --cn-name "Utility Fees" \
  --models UtilityConfig,UtilityBill \
  --contains UtilityConfig:name,remark \
  --exact UtilityConfig:enabled \
  --list-fields UtilityBill:room_id,billing_date,total_amount,status \
  --search-fields UtilityBill:room_id,billing_date,status
```

Advanced backend features are also available from the CLI:

```bash
uv run python -m app.cli crud hr \
  --cn-name HR \
  --models Employee,Department \
  --data-scope Employee:user_id,tenant_id \
  --button-auth \
  --soft-delete Employee \
  --tree Department \
  --list-order Employee:-created_at,id \
  --enable-routes Department:list,get \
  --list-cache Department:60 \
  --rate-limit Employee:30/60
```

| Option | Generated effect |
|---|---|
| `--data-scope Model:user_id,scope_id` | Overrides the list route and applies `build_scope_filter()`; business-scope lookup is emitted as `_get_scope_id()` |
| `--button-auth` | Declares menu buttons and attaches `require_buttons()` to create/edit/delete/batch_delete |
| `--soft-delete Model` | Emits `CRUDRouter(..., soft_delete=True)`; the model must use `SoftDeleteMixin` |
| `--tree Model` | Emits `CRUDRouter(..., tree_endpoint=True)`; the model must use `TreeMixin` or `parent_id` |
| `--list-cache Model:60` | Adds `@cache(expire=60, namespace=...)` to the list override; use only for low-cardinality lists |
| `--rate-limit Model:30/60` | Emits `ENDPOINT_RATE_LIMITS` in `api/manage.py`; startup auto-merges it into guard config |
| `--enable-routes Model:list,get` | Restricts the generated standard CRUD route set |
| `--exclude-fields Model:secret` | Sets fields excluded by `to_dict()` |

The `just` wrappers can pass extra CLI arguments through the final argument:

```bash
just cli-crud utility_fee "Utility Fees" "--yes --models UtilityConfig --button-auth"
```

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
# just cli-crud inventory Inventory

# 7. run migrations
just mm

# 8. start dev servers
just run

# 9. pre-push gate
just check
```
