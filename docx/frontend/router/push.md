# 路由跳转

`useRouterPush` 是基于 `vue-router` 的类型安全包装，路由 name 会被 TS 校验——拼错路由名编译期就会报错。

```ts
import { useRouterPush } from '@/hooks/common/router';

const {
  routerPush,           // 透传 router.push
  routerBack,           // router.back
  routerPushByKey,      // 按 RouteKey 跳转（推荐）
  toLogin,              // 跳到登录页
  toHome,               // 跳到当前用户首页
  redirectFromLogin,    // 登录后回跳到 redirect query
} = useRouterPush();
```

## 按 key 跳转（推荐）

`RouteKey` 由 Elegant Router 自动生成，所有合法的路由 name 都在这个联合类型里。

```ts
routerPushByKey('manage_user');                                 // → /manage/user
routerPushByKey('manage_user-detail', { params: { id: '1' } });  // → /manage/user-detail/1
routerPushByKey('function_request', {
  query: { from: 'home' }
});

// 新窗口打开
routerPushByKey('manage_user', undefined, true);
```

写错 key TypeScript 会立刻报错，比手敲路径安全。

## 直接跳路径

需要传字符串时（例如根据后端返回动态拼路径）：

```ts
routerPush('/manage/user');
routerPush({ path: '/manage/user', query: { tab: 'enabled' } });
```

## 登录 / 登录后回跳

```ts
toLogin();                       // 直接去登录页
toLogin('/manage/user');         // 登录成功后回跳到 /manage/user

redirectFromLogin();             // 登录页用：取 query.redirect 跳过去
```

`route.ts` 守卫在拦截未登录请求时已经把 `to.fullPath` 写到 `query.redirect`，登录页的"登录成功"回调直接 `redirectFromLogin()` 即可。

## 返回上一页

```ts
routerBack();                    // history.back
```

直接打开的某条详情链接没有 history 时，会自动 fallback 到首页，避免空白。

## 跳到当前用户首页

```ts
toHome();
```

首页路由名来自 `userInfo.role.routeHomeName`（后端按角色配的 `by_role_home`）。**同一个按钮**对超级管理员可能跳 `/manage/api`，对普通用户跳 `/home`——透明实现"按角色区分默认入口"。

## 在组件外调用

`useRouterPush` 必须在 setup / hook 上下文中调用。在 service / store 等"非组件"场景跳转时直接拿 router：

```ts
import { router } from '@/router';
router.push({ name: 'login' });
```

`web/src/router/index.ts` 把 router 实例 export 出来正是为了这种场景。

## 跳转动画 / loading

页面切换的进度条由 [src/router/guard/progress.ts](../../../web/src/router/guard/progress.ts) 用 NProgress 自动处理；无需手动接入。

## 相关

- [路由守卫](./guard.md)
- [创建路由](./create.md)
