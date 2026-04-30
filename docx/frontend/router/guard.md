# 路由守卫

每次路由跳转都会经过 `web/src/router/guard/` 的守卫链：认证 → 动态路由加载 → 权限校验 → 进度条 / 标题副作用。

## 守卫链组成

```
beforeEach (route.ts)
   │
   ├─ initRoute(to)                 # 首次进入：拉 user-info / user-routes / constant-routes，挂动态路由
   ├─ 已登录但去 login 页 → 回根
   ├─ 路由 meta.constant=true → 放行
   ├─ 未登录 → /login?redirect=<原 url>
   ├─ 已登录但 meta.roles 不匹配 → /403
   └─ 否则 → handleRouteSwitch（缓存更新 / tab push / multi-tab dedup）

beforeEach (progress.ts)            # 启动 NProgress
afterEach  (progress.ts)            # 完成 NProgress
afterEach  (title.ts)               # document.title = i18n(meta.title)
```

源码：[src/router/guard/](../../../web/src/router/guard/)。

## 守卫文件分工

| 文件 | 职责 |
|---|---|
| `route.ts` | 认证、动态路由加载、权限检查、tab 维护 |
| `progress.ts` | NProgress 加载进度条 |
| `title.ts` | 同步 `document.title`（带 i18n） |
| `index.ts` | 把上面三个串起来注册到 router |

## 守卫流程图

```
                  ┌─────────────────┐
路由跳转 ───────→  │  meta.constant?  │ ─Yes→ 放行
                  └────────┬────────┘
                           │No
                           ▼
                  ┌─────────────────┐
                  │  已登录?         │ ─No→  /login?redirect=...
                  └────────┬────────┘
                           │Yes
                           ▼
                  ┌─────────────────┐
                  │  动态路由已加载?  │ ─No→  GET /user-routes，挂载
                  └────────┬────────┘
                           │Yes
                           ▼
                  ┌─────────────────┐
                  │  meta.roles ⊂?  │ ─No→  /403
                  └────────┬────────┘
                           │Yes
                           ▼
                       放行 + tab push
```

## 常量路由

`meta.constant=true` 跳过所有认证检查。常用于：

| 路由 | 用途 |
|---|---|
| `login` | 登录页 |
| `403 / 404 / 500` | 错误页 |
| `home` | 首页（可见但通常需要登录后才能访问 — `home` 不是 constant） |
| `showcase` | HR 公开数据展示 Demo（`/showcase`）— 调用 `GET /api/v1/business/hr/public/showcase` |

后端 `Menu.constant=True` 会在启动时由 `load_constant_routes` 写到 Redis `constant_routes`；前端启动时拉一次，挂到 router。

### 新增一个常量路由

以 `/showcase`（HR 公开数据展示）为例——**前后端都要动**，缺一不可（在线 Demo：<https://fast-soy-admin.sleep0.de/showcase>）：

#### 1. 前端页面 + 白名单

- 在 [web/src/views/showcase/index.vue](../../../web/src/views/showcase/index.vue) 写页面（展示类页面用 `layout.blank` 更干净）。
- 把路由名加进 [web/build/plugins/router.ts](../../../web/build/plugins/router.ts) 的 `constantRoutes` 数组：

  ```ts
  const constantRoutes: RouteKey[] = ['login', '403', '404', '500', 'showcase'];
  ```

  `onRouteMetaGen` 会给它自动注入 `meta.constant = true`。启动 dev server 后 Elegant Router 会自动写回 [routes.ts](../../../web/src/router/elegant/routes.ts) / [imports.ts](../../../web/src/router/elegant/imports.ts) / [typings/elegant-router.d.ts](../../../web/src/typings/elegant-router.d.ts)。

#### 2. 后端 `Menu` 种子（dynamic 模式必须）

默认 `VITE_AUTH_ROUTE_MODE=dynamic` 时，前端启动会调用 `GET /api/v1/route/constant-routes` 从后端拉取，后端数据源是 `Menu.filter(constant=True, hide_in_menu=True)`。

**只在前端声明 `meta.constant: true` 会 404**——必须同时在 `init_data.py` 种一条 Menu：

```python
# app/business/<module>/init_data.py
await ensure_menu(
    menu_name="HR数据展示",
    route_name="showcase",
    route_path="/showcase",
    component="layout.blank$view.showcase",
    menu_type="1",
    constant=True,
    hide_in_menu=True,
    order=100,
)
```

然后**重启后端**：`init()` → 写 Menu → `refresh_all_cache()` → `load_constant_routes()` 刷新 Redis `constant_routes`。

> `static` 模式（`VITE_AUTH_ROUTE_MODE=static`）下前端自带全部路由声明，不需要 2 这一步。但本仓库默认 dynamic。

#### 3. 公开接口

接口放在 `/<module>/public/*` 前缀下，**不要**挂 `DependAuth / DependPermission`，**不要**返回 PII。详见 [HR 模块 · 公开接口](../../develop/business-hr.md#_5-公开接口-常量路由示例)。

## meta.roles（仅静态路由）

只有 `VITE_AUTH_ROUTE_MODE=static` 时 `meta.roles` 才生效——按用户当前角色集合做交集判断。

```typescript
meta: { roles: ['R_ADMIN', 'R_HR_ADMIN'] }
```

动态模式下 `meta.roles` 会被忽略（后端已经按角色过滤过了）。

## tab 与 multiTab 处理

`handleRouteSwitch` 会：

- 如果 `meta.multiTab=true` 且当前 query 不同 → 开新 tab
- 否则 → 复用同 routeName 的现有 tab
- 如果 `meta.fixedIndexInTab` 有值 → 把 tab 钉到指定位置

详见 `src/store/modules/tab/`。

## 自定义守卫

登录后做额外初始化（拉字典 / 拉用户偏好）时，在 `route.ts` 的 `initRoute` 里加一步即可。**不建议**新增独立的 `router.beforeEach`——容易和现有守卫的执行顺序冲突。

## 调试

```typescript
router.beforeEach((to, from) => {
  console.log('navigation', { from: from.fullPath, to: to.fullPath, meta: to.meta });
});
```

加在 `createRouter` 之后即可。生产环境记得删。

## 相关

- [动态路由](./dynamic.md)
- [路由跳转](./push.md)
- 后端：[认证](../../develop/auth.md)
