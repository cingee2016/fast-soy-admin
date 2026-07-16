# OPS Admin 项目总览

## 简介

OPS Admin 是基于 FastSoyAdmin 骨架改造的运维管理平台，采用 FastAPI + Vue3 全栈架构。

## 技术栈

- **后端**：FastAPI + Tortoise ORM + Redis + Python 3.12+
- **前端**：Vue3 + Vite + TypeScript + NaiveUI + UnoCSS + Pinia
- **工具链**：uv（Python）+ pnpm（Node.js）+ just（任务运行器）

## 模块清单

| 模块 | 说明 | 文档 |
|------|------|------|
| （待添加） | — | — |

## 前后端协作模型

- 后端提供 RESTful API（`/api/v1/`），前端通过 `@sa/axios` 调用
- 路由由后端动态下发（`VITE_AUTH_ROUTE_MODE=dynamic`）
- 权限校验：后端按钮权限 + 前端路由守卫

## ADR 索引

| 编号 | 标题 | 状态 |
|------|------|------|
| （待添加） | — | — |

## 骨架参考

原始骨架文档归档于 [docs/fast-soy-admin/](fast-soy-admin/)。
