# Create Routes

Business pages go live in three steps: create file → CLI generates → backend declares menu. **Prefer the CLI** — manual file creation is rare.

## Recommended: one-shot CLI

```bash
make cli-init MOD=inventory                 # backend module skeleton
# edit app/business/inventory/models.py to define models
make cli-gen-all MOD=inventory CN=Inventory  # generate frontend + backend
make mm                                      # migrate
make dev                                     # restart
```

The CLI produces:

- `web/src/views/inventory/<entity>/{index.vue, modules/*}` — list + drawer
- `web/src/service/api/inventory-manage.ts` — API calls
- `web/src/typings/api/inventory-manage.d.ts` — TS types
- `web/src/locales/langs/_generated/inventory/{zh-cn,en-us}.ts` — i18n fragment (merge into the main file)

See backend [Development guide](/en/getting-started/workflow).

## Manually create a new page

For non-CRUD pages (e.g. a custom dashboard):

### 1. Create the file

```bash
mkdir -p web/src/views/dashboard/sales
touch web/src/views/dashboard/sales/index.vue
```

```vue
<!-- web/src/views/dashboard/sales/index.vue -->
<script setup lang="ts">
defineOptions({ name: 'DashboardSales' });
</script>

<template>
  <div>Sales Dashboard</div>
</template>
```

On save, Elegant Router auto-detects and generates `dashboard_sales` → `/dashboard/sales`.

### 2. Declare the menu in the backend

In a business module's `init_data.py`'s `_init_menu_data`:

```python
{
    "menu_name": "Sales Dashboard",
    "route_name": "dashboard_sales",                # match the frontend route name
    "route_path": "/dashboard/sales",
    "component": "view.dashboard_sales",            # view + file path (_ replaces /)
    "icon": "mdi:chart-bar",
    "order": 1,
}
```

Add the `route_name` to the relevant role's `menus` list, restart the backend, and the user will see it after login.

### 3. Hidden routes (detail pages etc.)

Routes that exist but don't show in the menu (typically click-through detail pages):

```python
{
    "menu_name": "User detail",
    "route_name": "manage_user-detail",
    "route_path": "/manage/user-detail/:id",
    "component": "view.manage_user-detail",
    "hide_in_menu": True,
    "active_menu": "manage_user",       # highlight parent menu
}
```

Or via frontend route meta:

```typescript
meta: {
  title: 'User detail',
  hideInMenu: true,
  activeMenu: 'manage_user'
}
```

## Meta field cheat sheet

| Field | Use |
|---|---|
| `title` | route / menu title (overridden by `i18nKey`) |
| `i18nKey` | i18n key (preferred) |
| `icon` / `localIcon` | Iconify icon / local SVG |
| `order` | sibling sort |
| `hideInMenu` | hide from menu |
| `activeMenu` | "highlight parent" for hidden routes |
| `keepAlive` | cache via `<keep-alive>` |
| `multiTab` | allow multiple tabs of same route |
| `constant` | public route (no auth) |
| `roles` | only used when `VITE_AUTH_ROUTE_MODE=static` |
| `query` | fixed query params injected on navigation |

Full type in [src/typings/router.d.ts](../../../web/src/typings/router.d.ts) and the backend `Menu` model ([backend/models.md](/en/develop/models)).

## Common issues

### File created but no route generated

- Check the file name is valid (`kebab-case` or single words separated by `_`)
- Restart the Vite dev server
- `src/router/elegant/imports.ts` is auto-maintained; if it breaks, delete and restart

### Route accessible but missing from sidebar

The backend hasn't declared the `Menu`, or the current role's `menus` list doesn't contain this `route_name`.

## See also

- [Route structure](/en/frontend/router/structure)
- [Dynamic routes](/en/frontend/router/dynamic)
- Backend: [RBAC](/en/develop/rbac) / [Init data](/en/develop/init-data)
