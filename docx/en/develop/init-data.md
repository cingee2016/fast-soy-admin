# Startup Init & Reconciliation

Business modules declare menus, roles, buttons, and seed data via `init_data.py`. On every startup, autodiscover invokes each module's `init()`. Below: the sync semantics for each data category and how to make a module the single source of truth for its subtree.

## Startup flow

In `app/__init__.py`'s `lifespan`, the Redis-elected leader worker runs (in order):

1. `init_menus()` — system menus (`app/system/init_data.py`)
2. `refresh_api_list()` — **full reconciliation** of FastAPI routes ↔ `Api` table
3. `init_users()` — system seed users
4. iterate each business module's `init_data.init()` (HR, then any new modules)
5. `refresh_all_cache()` — reload permission / menu cache

Multi-worker coordination uses Redis lock `app:init_lock` so only one worker runs init; the rest wait for the done signal. The leader deletes stale locks before each start, so init really runs on every restart.

## Sync semantics by data type

| Data type | How it syncs | Field change | Add | Remove | Rename |
|---|---|---|---|---|---|
| **API** (routes) | `refresh_api_list` full reconcile | ✅ auto | ✅ auto | ✅ auto | ✅ auto (delete + insert) |
| **Menu** | `ensure_menu` upsert + optional `reconcile_menu_subtree` | ✅ auto | ✅ auto | ⚠️ requires reconcile | ⚠️ requires reconcile |
| **Button** | `ensure_menu` upsert + optional `reconcile_menu_subtree` | ✅ auto | ✅ auto | ⚠️ requires reconcile | ⚠️ requires reconcile |
| **Role** | `ensure_role` upsert; relations clear-and-readd | ✅ auto | ✅ auto | ❌ manual cleanup | ❌ manual cleanup |
| **Role grants** (menus / buttons / apis) | clear-and-readd | ✅ auto | ✅ auto | ✅ auto | ⚠️ missing emits warning |
| **Business seed data** | `_safe_update_or_create` by unique key | ✅ auto | ✅ auto | ❌ manual cleanup | ❌ manual cleanup |

Legend: ✅ takes effect on restart; ⚠️ needs explicit opt-in; ❌ needs SQL / migration.

## Menu / button reconciliation: `reconcile_menu_subtree`

`ensure_menu` is forward-applying (upsert only). Removing entries from `init_data.py` therefore doesn't clean the DB. `app/system/services/init_helper.py` provides `reconcile_menu_subtree` to scope an init declaration as the single source of truth for its subtree.

### Usage

In your module's `init_data.py` (see `app/business/hr/init_data.py`):

```python
from app.system.services import ensure_menu, reconcile_menu_subtree


def _collect_declared_routes(children: list[dict]) -> set[str]:
    result: set[str] = set()
    for item in children:
        result.add(item["route_name"])
        if item.get("children"):
            result.update(_collect_declared_routes(item["children"]))
    return result


def _collect_declared_buttons(children: list[dict]) -> set[str]:
    result: set[str] = set()
    for item in children:
        for btn in item.get("buttons") or []:
            result.add(btn["button_code"])
        if item.get("children"):
            result.update(_collect_declared_buttons(item["children"]))
    return result


async def _init_menu_data() -> None:
    await ensure_menu(
        menu_name="HR",
        route_name="hr",
        route_path="/hr",
        icon="mdi:account-group",
        order=8,
        children=HR_MENU_CHILDREN,
    )
    await reconcile_menu_subtree(
        root_route="hr",
        declared_route_names=_collect_declared_routes(HR_MENU_CHILDREN),
        declared_button_codes=_collect_declared_buttons(HR_MENU_CHILDREN),
    )
```

### Scope and semantics

- **Subtree-scoped**: BFS from `root_route`'s menu, only acts within that subtree
- **Menu reconciliation**: menus in the subtree whose `route_name` is not in `declared_route_names ∪ {root_route}` get `delete()`d (cascades M2M)
- **Button reconciliation**: only buttons mounted on subtree menus; those whose `button_code` is not in `declared_button_codes` get `delete()`d. Pass `declared_button_codes=None` to skip button reconciliation.
- **Idempotent**: re-running with no extras is a no-op

### Mental shift

After enabling `reconcile_menu_subtree`, that subtree becomes **Infrastructure-as-Code**:

- ✅ edit `init_data.py`, restart, done
- ✅ rename = delete-old + insert-new, auto handled
- ❌ **Web-UI-created menus / buttons under that subtree get reaped on next restart**

If you need user-driven dynamic menus, do **not** call `reconcile_menu_subtree` on that subtree.

## `ensure_role` config-drift warnings

`ensure_role` does clear-and-readd for `menus / buttons / apis`. If a declared `route_name / button_code / (method, path)` doesn't resolve in the DB, you get:

```
ensure_role 'R_DEPT_MGR': missing apis [('patch', '/api/v1/business/hr/departments/{dept_id}/old')] (route signature changed?)
```

Common causes:

- A route was renamed / removed but the seed `apis` wasn't updated
- A `button_code` was renamed but the seed `buttons` wasn't updated
- A parent `route_name` changed but the seed `menus` wasn't updated

**Fix on sight** — otherwise the role permission silently disappears and users hit mysterious 403s.

## Manual cleanup for removals

`reconcile_menu_subtree` only handles menus and buttons. The following still need **manual** cleanup (SQL or Tortoise migration):

1. **Roles** — removing `HR_ROLE_SEEDS` entries does NOT delete the `Role` row, nor does it touch user-role associations
2. **Business seed data** — same for `HR_DEPARTMENT_SEEDS / HR_TAG_SEEDS / HR_EMPLOYEE_SEEDS`
3. **Cross-subtree orphan buttons** — buttons referenced by multiple subtrees can survive cleanup of one of them

These scenarios are rare and removal cascades are subtle (does deleting a role also unbind its users?), so the framework intentionally avoids automation here — write a proper migration.

## Summary

| Scenario | Recommended action |
|---|---|
| Add menu / button / role / seed | Edit `init_data.py`, restart |
| Edit menu fields (name / icon / order) | Edit `init_data.py`, restart |
| Delete menu / button | Enable `reconcile_menu_subtree`, edit `init_data.py`, restart |
| Rename `route_name` / `button_code` | Enable `reconcile_menu_subtree`, restart auto delete-old + insert-new |
| Delete role / business seed | Write Tortoise migration |
| Modify API route path | Sync `apis` list in `HR_ROLE_SEEDS`, otherwise warning at startup |
