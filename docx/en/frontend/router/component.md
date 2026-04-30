# Route Component

The backend's `Menu.component` field decides which "layout + view" combo loads the route; the frontend transform maps the string to components.

## Component types

| `component` value | Meaning | When to use |
|---|---|---|
| `layout.base` | Main layout: sidebar / header / tabs / content / footer | top-level catalogs |
| `layout.blank` | Blank layout: only the view | login / error pages |
| `view.about` | View only (`views/about/index.vue`) | pages embedded in an existing layout |
| `layout.base$view.about` | Layout + view together (also a route root) | top-level standalone business routes |
| `layout.blank$view.login` | Blank layout + view | login |

## Naming map

`view.<route_name>`: treat `_` as `/`.

| route_name | File |
|---|---|
| `view.about` | `views/about/index.vue` |
| `view.manage_user` | `views/manage/user/index.vue` |
| `view.manage_user-detail` | `views/manage_user-detail/index.vue` |
| `view.function_multi-tab` | `views/function/multi-tab/index.vue` |
| `view.hr_employee` | `views/hr/employee/index.vue` |

`_` is the directory separator; multi-word path segments (`user-detail` / `multi-tab`) stay kebab.

## When `component=null`

- Top-level catalog (`catalog` menu) is just grouping — no view. `ensure_menu` infers automatically:
  - top + has children → `layout.base`
  - inner + has children → leave blank (catalog only)
  - leaf node → required; warning otherwise

Backend `ensure_menu` source: [app/system/services/init_helper.py](../../../app/system/services/init_helper.py).

## Custom layouts

To add a global layout (e.g. dual sidebar):

1. Add a component under `web/src/layouts/`, e.g. `dual-sidebar.vue`
2. Add `'dual-sidebar'` to `LayoutType` in `src/typings/router.d.ts`
3. Backend `Menu.component` uses `layout.dual-sidebar$view.xxx`

Rarely needed — `base` covers 95% of cases.

## Relationship with file structure

The route file structure ([Route structure](/en/frontend/router/structure)) decides **what routes exist**.
`component` decides **what shell renders them**.
They're independent — the same view can be reused across layouts (rare).

## See also

- [Route structure](/en/frontend/router/structure)
- [Create routes](/en/frontend/router/create)
- Backend: [Data models / Menu](/en/develop/models#menu)
