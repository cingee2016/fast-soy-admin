# 路由组件

后端 `Menu.component` 字段决定该路由用哪种"布局 + 视图组合"加载，前端 transform 时把字符串映射成实际组件。

## 组件类型

| `component` 值 | 含义 | 何时用 |
|---|---|---|
| `layout.base` | 主布局：含侧边栏 / 头部 / 标签页 / 内容区 / 底部 | 顶级目录（catalog） |
| `layout.blank` | 空白布局：直接渲染 view | 登录 / 错误页 |
| `view.about` | 仅 view 组件（`views/about/index.vue`） | 嵌在已有布局下的页面 |
| `layout.base$view.about` | 布局 + view 一并指定（同时是路由根） | 单独存在的顶级业务路由 |
| `layout.blank$view.login` | 空白布局 + view | 登录页 |

## 命名映射规则

`view.<route_name>`：把 `_` 反向当作 `/`。

| route_name | 对应文件 |
|---|---|
| `view.about` | `views/about/index.vue` |
| `view.manage_user` | `views/manage/user/index.vue` |
| `view.manage_user-detail` | `views/manage_user-detail/index.vue` |
| `view.function_multi-tab` | `views/function/multi-tab/index.vue` |
| `view.hr_employee` | `views/hr/employee/index.vue` |

`_` 做"目录分隔"，但出现在路径段内的多词（`user-detail` / `multi-tab`）保持 kebab。

## 何时填 `component=null`

- 顶级目录（`catalog` 类菜单）只是分组，不渲染具体 view，可以省略 `component`。`ensure_menu` 会按以下规则自动推断：
  - 顶级 + 有 `children` → `layout.base`
  - 内层 + 有 `children` → 不填（仅作目录）
  - 叶子节点 → 必须填（否则后端会 warning）

后端 `ensure_menu` 实现见 [app/system/services/init_helper.py](../../../app/system/services/init_helper.py)。

## 自定义布局

如果要新增一种全局布局（例如双侧栏），按以下步骤：

1. 在 `web/src/layouts/` 下加一个组件，如 `dual-sidebar.vue`
2. 在 `src/typings/router.d.ts` 的 `LayoutType` 补一个 `'dual-sidebar'`
3. 后端 `Menu.component` 用 `layout.dual-sidebar$view.xxx`

实际项目里几乎不需要——`base` 已覆盖大多数场景。

## 与文件结构的关系

路由文件结构（[路由结构](./structure.md)）决定**有哪些路由**。
`component` 决定**用什么外壳渲染**。
两者独立——同一个 view 可被不同布局复用（少见）。

## 相关

- [路由结构](./structure.md)
- [创建路由](./create.md)
- 后端：[数据模型 / Menu](../../develop/models.md#menu)
