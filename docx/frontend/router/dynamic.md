# 动态路由

默认**动态路由**：菜单 / 路由 meta 由后端按角色下发，前端登录后挂载到 vue-router。比"前端定义 + roles 过滤"的静态模式更安全、更灵活。

## 模式选择

```dotenv
# web/.env
VITE_AUTH_ROUTE_MODE=dynamic       # 默认；推荐
# VITE_AUTH_ROUTE_MODE=static      # 仅适合不需要细粒度后台管理的场景
```

| 模式 | 路由表来源 | 权限过滤 | 适用场景 |
|---|---|---|---|
| `dynamic` | 后端 `GET /api/v1/route/user-routes` | 后端按角色过滤后只下发可见路由 | 标准后台 |
| `static` | 前端 `views/` + `meta.roles` | 前端拿 `userInfo.roles` 过滤 | 简单 / 离线 demo |

::: warning 静态模式不安全
`static` 模式下"权限"只是 UI 隐藏，URL 直接访问仍能渲染——必须由后端 API 拒绝。生产环境用 `dynamic` 并配合后端 `DependPermission`。
:::

## 动态路由工作流

```
┌──────────────────────────────────────────────────┐
│ 1. 用户提交账号密码 → POST /api/v1/auth/login     │
│ 2. 拿到 token + refreshToken，存 localStorage    │
│ 3. GET /api/v1/auth/user-info                    │
│      → roles, buttons, mustChangePassword         │
│ 4. GET /api/v1/route/constant-routes              │
│      → 公共路由 (login / 403 / 404 / 500 / home)  │
│ 5. GET /api/v1/route/user-routes                  │
│      → 当前用户能看到的菜单树 + 默认首页 home      │
│ 6. 前端 transform 后挂到 vue-router               │
│ 7. 跳转到 home 或 redirect query                  │
└──────────────────────────────────────────────────┘
```

后端实现要点见 [src/router/guard/route.ts](../../../web/src/router/guard/route.ts) 与后端 [RBAC](../../develop/rbac.md)。

## 后端怎么决定可见路由

- 启动时由 leader worker 把每个角色的 `menu_ids` 写到 Redis `role:{code}:menus`
- `GET /user-routes` 时：
  - `R_SUPER` → 所有 `constant=False` 菜单
  - 其他角色 → 汇总该用户所有角色的 `menu_ids`，再补全父节点
- 转成菜单树后返回，前端挂到路由

## 路由 meta 在哪定义

| meta 字段 | 来源 |
|---|---|
| `title` / `i18nKey` | `Menu.menu_name` / `Menu.i18n_key` |
| `icon` / `localIcon` | `Menu.icon` + `Menu.icon_type` |
| `order` | `Menu.order` |
| `keepAlive` / `multiTab` / `hideInMenu` / `activeMenu` | 同名后端字段 |
| `constant` | `Menu.constant`（公共路由） |
| `href` | `Menu.href`（外链） |
| 组件 `component` | `Menu.component`（如 `view.manage_user`） |

## 切换/刷新动态路由

如果在管理后台改了角色 / 菜单，希望用户**当场生效**：

```typescript
import { useRouteStore } from '@/store/modules/route';

const routeStore = useRouteStore();
await routeStore.initAuthRoute();    // 重新拉取并挂载
```

或者推动用户重新登录。

::: tip 后端缓存的影响
路由数据来自 Redis 缓存（启动时灌入）。后端 CUD 后必须调 `load_role_permissions(redis, role_code=...)` 增量刷新，否则前端拉到的还是旧数据。详见后端 [缓存](../../ops/cache.md)。
:::

## 超级管理员行为

`R_SUPER` 拥有所有非常量菜单 + 所有按钮，且 `data_scope=all`。任何 `R_SUPER` 用户登录后：

- 路由树 = 全部 `Menu.filter(constant=False)`
- 按钮列表 = `Button.all()`
- 接口权限校验全部跳过

## 相关

- [路由结构](./structure.md)
- [路由守卫](./guard.md)
- 后端：[认证](../../develop/auth.md) / [RBAC](../../develop/rbac.md)
