# 路由结构

前端使用 [Elegant Router](https://github.com/soybeanjs/elegant-router) 由 `src/views/` 目录的文件结构**自动生成路由**。按约定建文件，路由表在保存时自动更新。

## 命名约定

| 文件结构 | 生成的路由 | 路由 name |
|---|---|---|
| `views/about/index.vue` | `/about` | `about` |
| `views/manage/user/index.vue` | `/manage/user` | `manage_user` |
| `views/manage/user/[id].vue` | `/manage/user/:id` | `manage_user_id` |
| `views/manage_user-detail/index.vue` | `/manage/user-detail` | `manage_user-detail` |

**关键规则**：

- 文件 / 目录名一律 `kebab-case` 或单词
- 路径段中需要小写多词时用 `-`（`user-detail`）
- 路径**层级** 用 `/` 表示文件夹层级
- 用 `_` 把两层路径**压平到同一个文件**：`views/manage_user-detail/index.vue` → `/manage/user-detail`
- 动态参数用方括号：`[id].vue` → `:id`

## 一级路由

```
views/about/index.vue       → /about            name=about
```

## 二级路由

```
views/manage/user/index.vue → /manage/user      name=manage_user
```

## 多级路由（避免文件夹深嵌套）

```
views/multi-menu/first/child/index.vue
                            → /multi-menu/first/child
                              name=multi-menu_first_child
```

## 参数路由

```
views/user/[id].vue         → /user/:id         name=user_id
```

## 自定义 / 内置路由

根路由 `/`、登录页、错误页等"非业务"路由在 [src/router/routes/builtin.ts](../../../web/src/router/routes/builtin.ts) 中手动声明。这些路由的 `meta.constant=true`，对所有用户始终可见，不走后端动态下发。

```typescript
// builtin.ts 示例
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
  // 403 / 404 / 500 ...
];
```

## 文件 → 路由的转换层

`src/router/elegant/transform.ts` 负责把 `views/` 文件结构 + 后端下发的菜单 dict 转成 vue-router 可用的路由对象。开发时**不需要**直接动它。

## 与后端的关系

| 角色 | 数据来源 |
|---|---|
| 路由文件结构 | 前端 `views/` 目录（开发时定义） |
| 路由 meta（title / icon / hideInMenu / ...） | 后端 `Menu` 表（`route_name` 为 key 关联） |
| 当前用户能看到哪些路由 | 后端 `GET /api/v1/route/user-routes` |
| 公共路由（登录 / 错误页） | 后端 `GET /api/v1/route/constant-routes`（启动后从 Redis 读） |

即：**前端定义"页面长什么样"，后端定义"谁能看到、按什么顺序、配什么图标"**。

## 相关

- [创建路由](./create.md)
- [动态路由](./dynamic.md)
- [路由组件](./component.md)
- 后端：[RBAC](../../develop/rbac.md)
