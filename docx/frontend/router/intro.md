# 系统路由

**动态路由**方案：菜单、API、按钮权限由后端统一管理，登录后按角色下发可访问路由。

::: danger
为支持 `<Transition>` 切换动画，`.vue` 的 `template` 只能有一个根元素，不能放注释或纯文本。
:::

## 路由来源

| 来源 | 何时加载 | 用途 |
|---|---|---|
| **常量路由**（`constantRoutes`） | 启动即加载 | 登录页、错误页、`/home` 等无需登录或所有角色均可访问的页面 |
| **动态路由**（后端下发） | 登录后从 `/api/v1/route/user-routes` 拉取 | 业务页面，按当前用户的角色过滤 |

前端路由守卫位于 `web/src/router/guard/`，负责：

1. 首次访问时调用用户信息接口（`/api/v1/auth/user-info`）
2. 拉取动态路由（`/api/v1/route/user-routes`）
3. 把远程路由挂到 Vue Router 上，并合并到菜单 Store

## 后端如何管理路由

菜单、API、按钮权限集中在 `app/system/models/admin.py` 的几张表：

| 表 | 职责 |
|---|---|
| `Menu` | 一级 / 二级 / 三级菜单，承载路由元信息（`route_name` / `route_path` / `component` / `icon` / `order` 等） |
| `Button` | 页面内按钮权限（`B_HR_CREATE` 之类的编码） |
| `Api` | 后端可调用接口集合（由启动钩子从 FastAPI 路由全量对账） |
| `Role` | 对上述三者的授权关系（M2M） |

业务模块通过 `init_data.py` 里的 `ensure_menu()` / `ensure_role()` 声明自己的路由和权限，详见 [启动初始化与对账](../../develop/init-data.md)。

## 前端页面文件组织

前端页面放在 `web/src/views/<module>/<entity>/`，每个实体常见结构：

```
web/src/views/inventory/warehouse/
├── index.vue                          # 列表页
└── modules/
    ├── warehouse-search.vue           # 搜索表单
    └── warehouse-operate-drawer.vue   # 新增 / 编辑抽屉
```

`component` 字段（数据库里）形如 `view.inventory_warehouse`，前端路由守卫会将其映射到 `src/views/inventory/warehouse/index.vue`。

## RouteMeta 属性

```typescript
interface RouteMeta {
  title: string;                  // 路由标题
  i18nKey?: App.I18n.I18nKey;    // 国际化 key（设置后忽略 title）
  roles?: string[];               // 允许访问的角色（后端下发时已按角色过滤）
  keepAlive?: boolean;            // 是否缓存
  constant?: boolean;             // 常量路由（无需登录）
  icon?: string;                  // Iconify 图标
  localIcon?: string;             // 本地 SVG 图标
  order?: number;                 // 菜单排序
  hideInMenu?: boolean;           // 在菜单中隐藏
  activeMenu?: string;            // 激活的菜单项（route name）
  multiTab?: boolean;             // 多标签页
  fixedIndexInTab?: number;       // 固定标签页顺序
  query?: { key: string; value: string }[];
}
```

图标来源：[icones.js.org](https://icones.js.org/)

## 新增一个业务路由

典型流程（以库存模块为例）：

1. 后端用 CLI 生成业务模块：`make cli-init MOD=inventory` → 写模型 → `make cli-gen MOD=inventory`
2. 前端用 CLI 生成页面：`make cli-gen-web MOD=inventory CN=库存管理`
3. 在模块的 `init_data.py` 中调用 `ensure_menu()` 注册菜单（一般生成器会留模板，用户补全）
4. `ensure_role()` 把菜单 / 按钮 / API 授权给对应角色
5. 重启后端，登录对应角色的用户即可看到菜单

完整步骤见 [开发指南](../../getting-started/workflow.md)。
