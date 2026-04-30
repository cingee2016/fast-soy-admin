# 前端简介

基于 [SoybeanAdmin](https://github.com/soybeanjs/soybean-admin)：Vue3 + Vite7 + TypeScript + Pinia + UnoCSS + Naive UI。`/web/` 是 pnpm workspace，业务代码在 `web/src/`，内部子包在 `web/packages/`。

## 技术栈

| 技术 | 版本 | 用途 |
|---|---|---|
| Vue | 3.5 | UI 框架 |
| Vite | 7 | 构建 |
| TypeScript | 5.9 | 类型 |
| Naive UI | 2.44 | 组件库 |
| Pinia | 3 | 状态管理 |
| UnoCSS | 66+ | 原子化 CSS |
| Alova | — | HTTP 客户端（业务请求） |
| vue-router | 4 | 动态路由（按角色下发） |
| vue-i18n | 11 | 国际化 |
| Elegant Router | — | 由 `views/` 目录自动生成路由 |
| unplugin-icons | — | 按需注册图标 |

## 目录结构

```
web/
├── src/
│   ├── views/                # 页面（Elegant Router 据此生成路由）
│   ├── service/              # HTTP 层（请求工厂 + API 函数）
│   │   ├── api/              # fetchXxx，按后端模块分文件
│   │   └── request/          # 拦截器 / 错误码 / token 刷新
│   ├── typings/              # TS 类型
│   │   ├── api/              # 与后端 schema 对应的接口类型
│   │   ├── app.d.ts
│   │   └── router.d.ts
│   ├── store/                # Pinia
│   │   └── modules/{auth,route,tab,theme,...}/
│   ├── router/               # vue-router 包装层
│   │   ├── elegant/          # 自动生成与转换
│   │   ├── guard/            # 守卫链（认证 / 动态路由 / 权限）
│   │   └── routes/builtin.ts # 公共路由（登录 / 错误页）
│   ├── hooks/                # 组合式函数（useTable / useAuth / ...）
│   ├── components/           # 全局组件
│   ├── layouts/              # 布局组件
│   ├── theme/                # 主题源（settings.ts / 类型 / 工具）
│   ├── locales/              # 国际化（zh-CN / en-US）
│   └── assets/svg-icon/      # 本地 SVG 图标
├── packages/                 # 内部子包
│   ├── alova/
│   ├── axios/
│   ├── hooks/
│   ├── utils/
│   ├── color/
│   └── uno-preset/
└── vite.config.ts
```

## 开发命令

```bash
cd web
pnpm install      # 安装依赖
pnpm dev          # 启动开发服务器（:9527）
pnpm build        # 生产构建
pnpm lint         # ESLint + oxlint
pnpm typecheck    # vue-tsc
```

也可以从项目根目录走 `make web-dev / web-build / web-lint / web-typecheck` 或一键 `make dev`（同时起前后端）。详见 [命令参考](../reference/commands.md)。

## 与后端的关系

前端**不**自己定义权限、不自己定义可见路由——这两类数据由后端按角色下发：

| 数据 | 来源 |
|---|---|
| 当前用户的角色 / 按钮权限 | `GET /api/v1/auth/user-info` |
| 公共路由（登录 / 错误页等） | `GET /api/v1/route/constant-routes` |
| 当前用户能看到的菜单树 | `GET /api/v1/route/user-routes` |
| 字典选项 | `GET /api/v1/system-manage/dictionaries/{type}/options` |

详细机制见 [动态路由](./router/dynamic.md) 与后端 [RBAC](../develop/rbac.md)。

## 子主题入口

| 主题 | 起点 |
|---|---|
| 路由 | [简介](./router/intro.md) → [结构](./router/structure.md) → [动态路由](./router/dynamic.md) |
| 请求 | [简介](./request/intro.md) → [使用方式](./request/usage.md) → [对接后端](./request/backend.md) |
| 主题 | [简介](./theme/intro.md) → [配置](./theme/config.md) → [UnoCSS 主题](./theme/unocss.md) |
| 图标 | [简介](./icon/intro.md) → [使用](./icon/usage.md) |
| Hooks | [useTable](./hooks/use-table.md) |

## 风格 & 规范

前端 SFC 写法、命名等约定见 [Vue 书写风格](../standard/vue.md) 与 [命名规范](../standard/naming.md)。
