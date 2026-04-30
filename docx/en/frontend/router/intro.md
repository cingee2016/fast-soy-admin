# System Routing

**Dynamic routing**: menus, APIs and button permissions are owned by the backend; each user receives their accessible routes after login based on roles.

::: danger
The `<Transition>` page-transition wrapper requires a single root element in every `.vue` `template` — no comments or plain text allowed.
:::

## Route sources

| Source | When loaded | Purpose |
|---|---|---|
| **Constant routes** (`constantRoutes`) | At app startup | Login, error pages, `/home` — pages with no auth requirement |
| **Dynamic routes** (backend-issued) | After login, fetched from `/api/v1/route/user-routes` | Business pages, filtered by the current user's roles |

Router guards live under `web/src/router/guard/` and are responsible for:

1. Calling the user info endpoint on first entry (`/api/v1/auth/user-info`)
2. Fetching dynamic routes (`/api/v1/route/user-routes`)
3. Mounting the remote routes on Vue Router and merging them into the menu store

## How the backend manages routes

Menus, APIs and button permissions are centralized in `app/system/models/admin.py`:

| Table | Responsibility |
|---|---|
| `Menu` | 1- to 3-level menus carrying route metadata (`route_name` / `route_path` / `component` / `icon` / `order` …) |
| `Button` | In-page button permissions (codes like `B_HR_CREATE`) |
| `Api` | Complete set of callable backend endpoints (reconciled from FastAPI routes at startup) |
| `Role` | Many-to-many grants over the three above |

Business modules declare their own routes and permissions via `ensure_menu()` / `ensure_role()` in `init_data.py`. See [Startup Init & Reconciliation](../../develop/init-data.md).

## Frontend page layout

Pages live under `web/src/views/<module>/<entity>/`. Typical structure:

```
web/src/views/inventory/warehouse/
├── index.vue                          # list page
└── modules/
    ├── warehouse-search.vue           # search form
    └── warehouse-operate-drawer.vue   # add / edit drawer
```

The `component` field stored in the DB (for example `view.inventory_warehouse`) is resolved by the router guard to `src/views/inventory/warehouse/index.vue`.

## RouteMeta

```typescript
interface RouteMeta {
  title: string;                  // route title
  i18nKey?: App.I18n.I18nKey;    // i18n key (takes precedence over title)
  roles?: string[];               // roles allowed (pre-filtered by the backend)
  keepAlive?: boolean;            // whether to keep alive
  constant?: boolean;             // constant route (no login required)
  icon?: string;                  // Iconify icon
  localIcon?: string;             // local SVG icon in src/assets/svg-icon
  order?: number;                 // menu sort order
  hideInMenu?: boolean;           // hide from menu
  activeMenu?: string;            // active menu item (route name)
  multiTab?: boolean;             // allow multiple tabs of the same path
  fixedIndexInTab?: number;       // fixed tab position
  query?: { key: string; value: string }[];
}
```

Icon source: [icones.js.org](https://icones.js.org/)

## Adding a business route

Typical workflow (using the inventory module):

1. Scaffold the backend module: `make cli-init MOD=inventory` → edit models → `make cli-gen MOD=inventory`
2. Generate the frontend pages: `make cli-gen-web MOD=inventory CN=Inventory`
3. Call `ensure_menu()` in the module's `init_data.py` to register the menu (the generator leaves a template; you fill in the details)
4. Use `ensure_role()` to grant menus / buttons / APIs to the appropriate roles
5. Restart the backend; users with that role will see the menu after logging in

Full walkthrough: [Development Guide](../../getting-started/workflow.md).
