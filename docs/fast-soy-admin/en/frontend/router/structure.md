# Route Structure

The frontend uses [Elegant Router](https://github.com/soybeanjs/elegant-router) to **auto-generate routes** from `src/views/`. Create files following the convention; the route table updates on save.

## Naming convention

| File structure | Generated route | name |
|---|---|---|
| `views/about/index.vue` | `/about` | `about` |
| `views/manage/user/index.vue` | `/manage/user` | `manage_user` |
| `views/manage/user/[id].vue` | `/manage/user/:id` | `manage_user_id` |
| `views/manage_user-detail/index.vue` | `/manage/user-detail` | `manage_user-detail` |

**Key rules**:

- Files / folders are `kebab-case` or single words
- Multi-word path segments use `-` (`user-detail`)
- `/` represents folder hierarchy
- `_` collapses two path levels into a single file: `views/manage_user-detail/index.vue` → `/manage/user-detail`
- Brackets denote dynamic params: `[id].vue` → `:id`

## Single level

```
views/about/index.vue       → /about            name=about
```

## Two levels

```
views/manage/user/index.vue → /manage/user      name=manage_user
```

## Multi-level (avoid deep folders)

```
views/multi-menu/first/child/index.vue
                            → /multi-menu/first/child
                              name=multi-menu_first_child
```

## Param routes

```
views/user/[id].vue         → /user/:id         name=user_id
```

## Custom / built-in routes

The root `/`, login page, and error pages — non-business routes — are declared manually in `src/router/routes/builtin.ts`. Their `meta.constant=true` makes them visible to everyone and not delivered by the backend.

```typescript
export const builtinRoutes: ElegantConstRoute[] = [
  {
    name: 'root',
    path: '/',
    redirect: getRouteHome().name,
    meta: { title: 'root', constant: true }
  },
  {
    name: 'login',
    path: '/login',
    component: 'layout.blank$view.login',
    props: true,
    meta: { title: 'login', constant: true }
  },
];
```

## File → route transform

`src/router/elegant/transform.ts` turns the `views/` structure + the backend menu dict into vue-router objects. Rarely touched directly.

## Relationship with the backend

| Concern | Source |
|---|---|
| Route file structure | Frontend `views/` (defined at dev time) |
| Route meta (title / icon / hideInMenu / ...) | Backend `Menu` table (joined by `route_name`) |
| Routes the current user can see | Backend `GET /api/v1/route/user-routes` |
| Public routes (login / error) | Backend `GET /api/v1/route/constant-routes` (read from Redis at startup) |

In short: **the frontend defines what each page looks like; the backend defines who can see it, in what order, with which icon**.

## See also

- [Create routes](/en/frontend/router/create)
- [Dynamic routes](/en/frontend/router/dynamic)
- [Route component](/en/frontend/router/component)
- Backend: [RBAC](/en/develop/rbac)
