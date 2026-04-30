# 简介

[FastSoyAdmin](https://github.com/sleep1223/fast-soy-admin) 是一套开箱即用的全栈后台管理模板。

- **前端** — 基于 [SoybeanAdmin](https://github.com/soybeanjs/soybean-admin)，Vue3 + Vite7 + TypeScript + Pinia + UnoCSS + Naive UI
- **后端** — FastAPI + Pydantic v2 + Tortoise ORM + Redis，"系统模块 + 业务模块"分层，业务模块自动发现

monorepo 结构：`/app` 后端，`/web` 前端，`/deploy` Docker / Nginx。

## 特性

**AI 驱动**

- **AI Coding 友好** — 仓库内置 `CLAUDE.md` + `llms.txt` / `llms-full.md`，把架构约定、分层职责、API 规范、响应码表、PR checklist 一次喂给 Claude Code / Cursor / Copilot，AI 直接按项目规范产出代码
- **生成器即 AI 工作面** — `make cli-gen-all` 把"加一张表"压缩成单条命令，AI 只关注 `models.py` 业务建模与覆写差异，剩余 90% 模板由 CLI 完成

**工程效率**

- **CLI 端到端生成** — `make cli-init / cli-gen-all` 从 Tortoise 模型一键产出前后端 CRUD（schemas / controllers / api + views / service / typings / i18n）
- **CRUDRouter + `@crud.override`** — 标准 6 路由由工厂统一生成，差异部分按需覆写，并显式划定"聚合根禁用"边界，避免抽象上瘾

**可扩展架构**

- **业务模块自动发现** — `app/business/<x>/` 放进去就自动注册路由、模型、初始化数据；模块互不耦合，跨模块走事件总线（`emit` / `on`）
- **多库友好** — 业务模块可声明独立 `DB_URL` 注册成 `conn_<biz>`；事务一律 `in_transaction(get_db_conn(Model))`
- **多 worker 启动协调** — Redis leader 锁串行执行 `init_menus → refresh_api_list → init_data → refresh_cache`，K8s 多副本无重复对账

**安全与权限**

- **三层 RBAC + 行级 `data_scope`** — 菜单 / API / 按钮三层鉴权，叠加 `all / department / self / custom` 数据范围；按钮权限下沉到 service
- **菜单/角色 IaC 对账** — `ensure_menu` / `reconcile_menu_subtree` / `refresh_api_list` 三档语义，明确哪些子树代码声明、哪些允许 UI 自由创建
- **Sqid 对外 ID** — 自增 ID 不出库，防遍历枚举

**契约与类型**

- **统一响应** — `{code, msg, data}` + HTTP 200 + camelCase 自动转换；业务异常 `BizError` 穿透，唯一业务码
- **全栈类型安全** — 前端 vue-tsc，后端 basedpyright（standard），CI 强制全绿
- **i18n 静态校验** — 生成的 i18n 经 `import.meta.glob` 自动并入，`App.I18n.GeneratedPages` 让 `$t` 键被 vue-tsc 校验

**可观测与稳定性**

- **内置 Radar 面板** — 实时请求 / SQL / 异常 / 权限拒绝日志
- **fastapi-guard 限流 + IP 封禁** — 暴力破解、扫描自动拦截
- **Redis 缓存 + 降级** — 角色权限 / 常量路由 / token_version 缓存优先，Redis 故障回落 DB
- **状态机 / 事件总线** — 工单、审批、订单等状态流转开箱即用

**部署**

- **Docker 一键部署** — Nginx + FastAPI + Redis 编排好，`docker compose up -d` 即可上线

## 文档怎么读

| 目标 | 入口 |
|---|---|
| 跑起来 | [快速开始](./quick-start.md) |
| 加业务模块 | [开发指南](./workflow.md) |
| 后端架构 / 自动发现 / RBAC | [后端简介](../develop/intro.md) → [架构](./architecture.md) |
| 前端路由 / 请求 / 主题 | [前端简介](../frontend/intro.md) |
| 提交前规范 | [后端规范](../standard/backend.md) · [Vue 风格](../standard/vue.md) · [命名](../standard/naming.md) |
| 部署 | [部署](../ops/deployment.md) |
| 报错排查 | [常见问题](../faq/) |

## 架构总览

```
┌─────────────────────────────────────────────────┐
│                  Nginx (:1880)                  │
│        静态资源 + /api/* 反向代理                │
├──────────────────────┬──────────────────────────┤
│   前端 (:9527)        │   后端 (:9999)           │
│   Vue3 + Vite7       │   FastAPI                │
│                      │                          │
│   Views              │   api/                   │
│     ↓                │     ↓                    │
│   Pinia              │   services/              │
│     ↓                │     ↓                    │
│   Alova ─────────────┼─→ /api/v1/*              │
│                      │     ↓                    │
│                      │   controllers (CRUDBase) │
│                      │     ↓                    │
│                      │   Tortoise / Redis       │
└──────────────────────┴──────────────────────────┘
```

## 链接

- [在线预览](https://fast-soy-admin.sleep0.de/)
- [GitHub 仓库](https://github.com/sleep1223/fast-soy-admin)
- [API 文档 (Apidog)](https://fast-soy-admin.apidog.io)
- [SoybeanAdmin（前端上游）](https://github.com/soybeanjs/soybean-admin)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Tortoise ORM](https://tortoise.github.io)
