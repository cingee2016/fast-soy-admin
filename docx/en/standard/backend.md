# Backend Style

Enforced checklist for backend code — usable as a PR review checklist. Covers response, schema, API path, CRUD, permissions, exceptions, cache, and naming.

::: warning Not soft suggestions
Each item below is "to fix". Deviations require explicit justification in the PR description.
:::

## 1. Response

- ✅ Use `Success` / `SuccessExtra` / `Fail` from `app.utils`
- ❌ Don't return raw dicts, raw `JSONResponse(...)`, or `{"code": "0000", ...}` literals
- ❌ Don't hand-roll snake_case responses — `SchemaBase` / `to_dict()` already do camelCase
- ✅ Each distinct failure scenario gets a **unique business code** (append to `app/core/code.py`); avoid `Code.FAIL` as a catch-all
- ✅ Raise `BizError(code, msg)` (transparent across layers); use `return Fail(...)` only at the api layer

```python
# ✅
return Success(data=await user.to_dict())
return SuccessExtra(data={"records": records}, total=total, current=obj_in.current, size=obj_in.size)
raise BizError(code=Code.HR_INVALID_TRANSITION, msg="invalid transition")

# ❌
return {"code": "0000", "data": {...}}
return JSONResponse({"code": Code.FAIL, "msg": "fail"})
```

## 2. Schema

- ✅ Business schemas **must** inherit `SchemaBase` (auto snake_case ↔ camelCase)
- ✅ Pagination search schemas **must** inherit `PageQueryBase`
- ✅ Use `SqidId` for resource ID fields, `SqidPath` for FastAPI path params
- ✅ Use `Int16 / Int32 / Int64` for integer fields aligned to the column type
- ✅ Derive Update schemas via `make_optional(XxxCreate, "XxxUpdate")` to avoid duplication
- ❌ Don't `from pydantic import BaseModel as ...` in business code — use `from app.utils import SchemaBase`
- ✅ Use `SchemaValidationError(code, msg)` in validators when you need a specific business code, **not** `ValueError`

## 3. API path & method

- ✅ List: `POST /resources/search`, body inherits `PageQueryBase`
- ✅ Single: `GET / PATCH / DELETE /resources/{id}` (id is sqid)
- ✅ Create: `POST /resources`
- ✅ Batch delete: `DELETE /resources` with `CommonIds` body
- ✅ Multi-word paths use **kebab-case** (`/batch-offline`, `/user-routes`)
- ✅ Resource names are **plural**
- ❌ No trailing slashes
- ❌ Don't implement complex search via `GET /resources?...` — always use `POST /search`

See full convention in [API conventions](/en/develop/api).

## 4. Routing layer (CRUD)

- ✅ Use `CRUDRouter` for the standard 6; **never** hand-write them
- ✅ Customize a route via `@crud.override("create")`; **don't** redeclare the same path on the router
- ✅ Mount button permissions on `action_dependencies` — they apply to `@override` routes too
- ✅ Mount endpoints beyond the standard 6 directly on `crud.router`
- ❌ Don't mutate `router.routes.append(...)` — bypasses `_OrderedRouter` sorting
- ❌ Controllers / services don't `import fastapi.Request` — HTTP only at the api layer
- ❌ Inside `@crud.override`, **forbid** `in_transaction` / `request.app.state.redis` / cross-model writes / events / audit — push these down into `services/`; the api layer only forwards arguments and wraps responses
- ❌ When a resource has ≥ 3 overrides, or is an aggregate root (stateful, side-effect-heavy), **switch to** explicit `@router.post(...)` + `services/` — don't force-fit `CRUDRouter` (it serves only anemic resources)

## 5. Layer responsibilities

| Layer | Must do | Must not do |
|---|---|---|
| `api/` | URL wiring, dependencies, `Success`/`Fail` | business rules, cross-model, transactions |
| `services/` | transactions, cross-model, cache, FSM, events | touch HTTP (Request/Response) |
| `controllers/` | single-resource CRUD (extend `CRUDBase`), `build_search` | cross-model side effects |
| `models/` | columns, indexes, relations, mixins | business validation |
| `schemas/` | DTOs and field-level validation | cross-resource logic |

## 6. Permissions

- ✅ Write endpoints (POST/PATCH/DELETE) **must** mount button permissions (`require_buttons` or `action_dependencies`)
- ✅ Business role seeds **must** explicitly set `data_scope` (don't rely on the model default `all`)
- ✅ List endpoints with row-level scope **must** `@override("list")` and apply `build_scope_filter`
- ❌ Never rely on "frontend hides the button" for security — backend must enforce
- ❌ Don't hard-compare `role_code == "R_HR_ADMIN"` in business code — use `has_role_code` / `has_button_code`

## 7. Models

- ✅ Models inherit `BaseModel + AuditMixin` (for persisted models)
- ✅ Top of the file: `# pyright: reportIncompatibleVariableOverride=false` (Tortoise + Pyright known false positive)
- ✅ Add `description="..."` to every field (CLI uses it as i18n label, truncated to first sentence)
- ✅ Class docstring is the Chinese resource name (`"""Department"""`); used as API summary prefix
- ✅ `Meta.table` uses `biz_<module>_<entity>` prefix (system models in `app/system/models/` use semantic table names)
- ❌ No business logic in `models.py` — validation in schema, side effects in service

## 8. Business module boundaries

- ✅ Business modules import via `app.utils` only
- ✅ Cross-business communication goes through the [Event bus](/en/develop/events) (`emit` / `on`)
- ❌ Business modules **never reverse-import** `app.system.*` (except for the few services system explicitly exposes — `ensure_menu` / `ensure_role` / ...)
- ❌ Business modules **never import each other** (`app.business.crm.*` cannot import `app.business.hr.*`)

## 9. Naming

- File / dir: `snake_case`
- Class: `PascalCase`
- Function / method: `snake_case`
- Constant: `UPPER_SNAKE_CASE`
- API path: `kebab-case`
- Schema field (Python internal): `snake_case`; HTTP boundary (frontend-visible): `camelCase`
- Role code: `R_<UPPER>` / Button: `B_<MODULE>_<RESOURCE>_<ACTION>` / Route name: `module_subpage`

See [Naming](/en/standard/naming).

## 10. Type hints / format / lint

- ✅ Type-hint every function
- ✅ Pre-push:

```bash
make fmt          # ruff check --fix + format
make typecheck    # basedpyright
make test         # pytest
make check        # all three above
```

- ✅ Line 200, double-quote, sorted imports
- ✅ basedpyright standard mode must pass

## 11. Exception handling

- ✅ Raise `BizError` / `SchemaValidationError` for business errors
- ❌ Don't `raise HTTPException` (legacy alias only kept for compatibility — new code uses `BizError`)
- ❌ Don't `except Exception:` and swallow — let the global handler log it
- ✅ Multi-step writes that need rollback use `in_transaction(get_db_conn(Model))` in a service
- ❌ Don't hard-code connection names (`"conn_system"`); use `get_db_conn(Model)`

## 12. Cache

- ✅ Module-local hot data (stats / options) follow "read → miss → query → write with TTL"
- ✅ **Actively invalidate** cache keys on data change (module's `cache_utils.py`)
- ❌ Don't slap `@cache(...)` on paginated / multi-param endpoints
- ✅ Business key naming: `<module>_<resource>:<scope>` (e.g. `dict_options:tag_category`)

See [Cache](/en/ops/cache).

## 13. Logging & monitoring

- ✅ Use `radar_log` for key business nodes / permission denials / exception branches
- ✅ Use `log.debug(...)` for high-frequency debug; not everything needs to hit Radar
- ❌ No `print(...)`

## 14. Pre-push gate

```bash
make check-all    # backend + frontend full quality check
```

Includes: `ruff fix + format`, `basedpyright`, `pytest`, `eslint + oxlint`, `vue-tsc`.

## See also

- [Architecture](/en/getting-started/architecture)
- [Development guide](/en/getting-started/workflow)
- [API conventions](/en/develop/api) / [Response codes](/en/reference/codes)
- [HR module (best-practice reference)](/en/develop/business-hr)
