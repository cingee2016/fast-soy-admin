# 创建路由

业务页面通过"建文件 → CLI 生成 → 后端声明菜单"三步上线，**多数场景用 CLI 一键生成**，不需要手动建。

## 推荐：CLI 一键生成

```bash
make cli-init MOD=inventory                  # 创建后端模块骨架
# 编辑 app/business/inventory/models.py 定义模型
make cli-gen-all MOD=inventory CN=库存管理   # 同时生成前后端
make mm                                      # 数据库迁移
make dev                                     # 重启
```

CLI 自动产出：

- `web/src/views/inventory/<entity>/{index.vue, modules/*}` — 列表页 + 抽屉
- `web/src/service/api/inventory-manage.ts` — API 调用
- `web/src/typings/api/inventory-manage.d.ts` — TS 类型
- `web/src/locales/langs/_generated/inventory/{zh-cn,en-us}.ts` — i18n 片段（手动合并到主文件）

详见后端 [开发指南](../../getting-started/workflow.md)。

## 手动建一个新页面

添加不走 CRUD 的页面（例如自定义看板）：

### 1. 建文件

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

保存后 Elegant Router 会自动检测并生成路由 `dashboard_sales` → `/dashboard/sales`。

### 2. 在后端声明菜单

打开（或新建）一个业务模块的 `init_data.py`，往 `_init_menu_data` 里加：

```python
{
    "menu_name": "销售看板",
    "route_name": "dashboard_sales",                # 与前端 route name 一致
    "route_path": "/dashboard/sales",
    "component": "view.dashboard_sales",            # view + 文件路径（_ 替换 /）
    "icon": "mdi:chart-bar",
    "order": 1,
}
```

把 `route_name` 加进对应角色的 `menus` 列表，重启后端，对应用户登录就能看到。

### 3. 隐藏路由（详情页等）

不需要在菜单显示但路由要存在（例如点列表里的"查看详情"跳转过去）：

```python
{
    "menu_name": "用户详情",
    "route_name": "manage_user-detail",
    "route_path": "/manage/user-detail/:id",
    "component": "view.manage_user-detail",
    "hide_in_menu": True,
    "active_menu": "manage_user",       # 高亮父菜单
}
```

或者前端路由 meta：

```typescript
meta: {
  title: '用户详情',
  hideInMenu: true,
  activeMenu: 'manage_user'
}
```

## meta 字段速览

| 字段 | 用途 |
|---|---|
| `title` | 路由 / 菜单标题（被 `i18nKey` 覆盖） |
| `i18nKey` | 国际化 key（推荐使用） |
| `icon` / `localIcon` | Iconify 图标 / 本地 SVG |
| `order` | 同层菜单排序 |
| `hideInMenu` | 在菜单中隐藏 |
| `activeMenu` | 隐藏路由的"高亮父菜单" |
| `keepAlive` | 是否缓存（`<keep-alive>`） |
| `multiTab` | 是否允许同路由多 tab |
| `constant` | 公共路由（无需登录） |
| `roles` | 仅当 `VITE_AUTH_ROUTE_MODE=static` 时按角色过滤 |
| `query` | 跳转时附带的固定 query 参数 |

完整定义见 [src/typings/router.d.ts](../../../web/src/typings/router.d.ts) 与后端 `Menu` 模型字段（[backend/models.md](../../develop/models.md)）。

## 常见问题

### 文件建好但路由没生成

- 检查文件名是否合法（`kebab-case` 或单词 + `_` 分隔）
- 重启 Vite 开发服务器
- `src/router/elegant/imports.ts` 由 Elegant Router 自动维护；坏了可删掉重启

### 前端能进路由但侧边栏看不到

后端没声明 `Menu` 或者当前角色的 `menus` 列表里没有这个 `route_name`。

## 相关

- [路由结构](./structure.md)
- [动态路由](./dynamic.md)
- 后端：[RBAC](../../develop/rbac.md) / [启动初始化与对账](../../develop/init-data.md)
