# Route Guards

Every navigation goes through guards in `web/src/router/guard/`: auth → dynamic route loading → permission check → progress bar / title side effects.

## Guard chain

```
beforeEach (route.ts)
   │
   ├─ initRoute(to)                 # first entry: fetch user-info / user-routes / constant-routes, mount routes
   ├─ already logged in but going to /login → return to root
   ├─ meta.constant=true → pass
   ├─ not logged in → /login?redirect=<original url>
   ├─ logged in but meta.roles mismatch → /403
   └─ otherwise → handleRouteSwitch (cache update / tab push / multi-tab dedup)

beforeEach (progress.ts)            # start NProgress
afterEach  (progress.ts)            # finish NProgress
afterEach  (title.ts)               # document.title = i18n(meta.title)
```

Source: [src/router/guard/](../../../web/src/router/guard/).

## Files

| File | Responsibility |
|---|---|
| `route.ts` | auth, dynamic route loading, permission check, tab management |
| `progress.ts` | NProgress |
| `title.ts` | sync `document.title` (with i18n) |
| `index.ts` | wires the above into the router |

## Flow chart

```
                  ┌─────────────────┐
navigation ─────→ │  meta.constant?  │ ─Yes→ pass
                  └────────┬────────┘
                           │No
                           ▼
                  ┌─────────────────┐
                  │  logged in?      │ ─No→  /login?redirect=...
                  └────────┬────────┘
                           │Yes
                           ▼
                  ┌─────────────────┐
                  │  routes loaded?  │ ─No→  GET /user-routes, mount
                  └────────┬────────┘
                           │Yes
                           ▼
                  ┌─────────────────┐
                  │  meta.roles ⊂?  │ ─No→  /403
                  └────────┬────────┘
                           │Yes
                           ▼
                       pass + tab push
```

## Constant routes

`meta.constant=true` skips all auth checks. Common cases:

| Route | Use |
|---|---|
| `login` | login |
| `403 / 404 / 500` | error pages |
| `home` | home (typically requires login — `home` is NOT constant) |
| `showcase` | HR public data showcase demo (`/showcase`) — calls `GET /api/v1/business/hr/public/showcase` |

The backend writes `Menu.constant=True` rows into Redis `constant_routes` via `load_constant_routes`; the frontend fetches once at startup.

### Adding a new constant route

Using `/showcase` (HR public data showcase) as the example — **both frontend and backend must be updated**, neither can be skipped (live demo: <https://fast-soy-admin.sleep0.de/showcase>):

#### 1. Frontend page + whitelist

- Write the page at [web/src/views/showcase/index.vue](../../../web/src/views/showcase/index.vue) (display-only pages look cleaner under `layout.blank`).
- Add the route name to the `constantRoutes` array in [web/build/plugins/router.ts](../../../web/build/plugins/router.ts):

  ```ts
  const constantRoutes: RouteKey[] = ['login', '403', '404', '500', 'showcase'];
  ```

  `onRouteMetaGen` automatically injects `meta.constant = true`. After the dev server starts, Elegant Router writes back [routes.ts](../../../web/src/router/elegant/routes.ts) / [imports.ts](../../../web/src/router/elegant/imports.ts) / [typings/elegant-router.d.ts](../../../web/src/typings/elegant-router.d.ts).

#### 2. Backend `Menu` seed (required in dynamic mode)

With the default `VITE_AUTH_ROUTE_MODE=dynamic`, the frontend calls `GET /api/v1/route/constant-routes` at startup; the backend source is `Menu.filter(constant=True, hide_in_menu=True)`.

**Declaring `meta.constant: true` only on the frontend will 404** — you must also seed a Menu row in `init_data.py`:

```python
# app/business/<module>/init_data.py
await ensure_menu(
    menu_name="HR Showcase",
    route_name="showcase",
    route_path="/showcase",
    component="layout.blank$view.showcase",
    menu_type="1",
    constant=True,
    hide_in_menu=True,
    order=100,
)
```

Then **restart the backend**: `init()` → write Menu → `refresh_all_cache()` → `load_constant_routes()` refreshes Redis `constant_routes`.

> In `static` mode (`VITE_AUTH_ROUTE_MODE=static`) the frontend ships all route declarations itself, so step 2 is unnecessary. This repo defaults to dynamic.

## meta.roles (static mode only)

Only when `VITE_AUTH_ROUTE_MODE=static` does `meta.roles` apply — intersect with the user's current roles.

```typescript
meta: { roles: ['R_ADMIN', 'R_HR_ADMIN'] }
```

In dynamic mode `meta.roles` is ignored (the backend already filtered).

## Tab and multiTab handling

`handleRouteSwitch`:

- `meta.multiTab=true` and the query is different → open a new tab
- otherwise → reuse the existing tab with the same routeName
- `meta.fixedIndexInTab` set → pin tab to that index

See `src/store/modules/tab/`.

## Custom guards

Need extra init after login (load dictionaries / user prefs)? Add it inside `route.ts`'s `initRoute`. **Don't** add a separate `router.beforeEach` — it clashes with existing guard ordering.

## Debug

```typescript
router.beforeEach((to, from) => {
  console.log('navigation', { from: from.fullPath, to: to.fullPath, meta: to.meta });
});
```

Add after `createRouter`. Remove in production.

## See also

- [Dynamic routes](/en/frontend/router/dynamic)
- [Router push](/en/frontend/router/push)
- Backend: [Auth](/en/develop/auth)
