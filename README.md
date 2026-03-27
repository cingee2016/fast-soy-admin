<!-- markdownlint-disable MD033 MD041 -->

<p align="center">
  <a href="https://github.com/sleep1223/"><img src="web/public/favicon.svg" width="200" height="200" alt="github"></a>
</p>

<div align="center">

# FastSoyAdmin

<!-- prettier-ignore-start -->
<!-- markdownlint-disable-next-line MD036 -->

[![license](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![github stars](https://img.shields.io/github/stars/sleep1223/fast-soy-admin)](https://github.com/sleep1223/fast-soy-admin)
[![github forks](https://img.shields.io/github/forks/sleep1223/fast-soy-admin)](https://github.com/sleep1223/fast-soy-admin)
![python](https://img.shields.io/badge/python-3.12+-blue?logo=python&logoColor=edb641)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?logo=python&logoColor=edb641)

![Pydantic](https://img.shields.io/badge/Pydantic_v2-005571?logo=pydantic&logoColor=edb641)
![uv](https://img.shields.io/badge/uv-managed-blueviolet)
[![pyright](https://img.shields.io/badge/types-pyright-797952.svg?logo=python&logoColor=edb641)](https://github.com/Microsoft/pyright)
[![ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

<span><a href="./README.en.md">English</a> | 中文</span>

</div>

> [!NOTE]
> 如果 `FastSoyAdmin` 对你有帮助，欢迎在 GitHub 上点个 ⭐️，这是对我们最大的鼓励！

## 简介

[`FastSoyAdmin`](https://github.com/sleep1223/fast-soy-admin) 是一套开箱即用的全栈后台管理模板。前端基于 Vue3、Vite7、TypeScript、Pinia 和 UnoCSS 构建，后端采用 FastAPI、Pydantic v2 和 Tortoise ORM，并通过 Redis 加速接口响应。项目内置丰富的主题配置、完整的 RBAC 权限控制、自动化文件路由以及多语言支持，适合作为中后台项目的起步脚手架，也适合用来学习全栈开发的最佳实践。

[![DeepWiki](https://img.shields.io/badge/DeepWiki-sleep1223%2Ffast--soy--admin-blue?logo=data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIHZpZXdCb3g9IjAgMCAzMiAzMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHJlY3Qgd2lkdGg9IjMyIiBoZWlnaHQ9IjMyIiByeD0iOCIgZmlsbD0iIzFFOTBGRiIvPgo8cGF0aCBkPSJNOCAxMEgxMlYyMkg4VjEwWiIgZmlsbD0id2hpdGUiLz4KPHBhdGggZD0iTTE1IDEwSDE5VjIySDE1VjEwWiIgZmlsbD0id2hpdGUiIG9wYWNpdHk9IjAuNyIvPgo8cGF0aCBkPSJNMjIgMTBIMjZWMjJIMjJWMTBaIiBmaWxsPSJ3aGl0ZSIgb3BhY2l0eT0iMC40Ii8+Cjwvc3ZnPg==)](https://deepwiki.com/sleep1223/fast-soy-admin)

## 特性

- **全栈技术栈**：后端 FastAPI + Pydantic v2 + Tortoise ORM，前端 Vue3 + Vite7 + TypeScript + Pinia + UnoCSS，前后端均采用主流技术方案。
- **完整的权限体系**：基于 RBAC 模型，前后端角色权限严格分离，后端对 API 和按钮级别进行二次鉴权，确保安全可控。
- **日志与审计**：内置请求日志和操作日志管理，便于排查问题和审计追踪。
- **Redis 缓存加速**：集成 fastapi-cache2 + Redis，有效提升接口响应速度。
- **清晰的项目结构**：采用 pnpm monorepo 管理，后端分层架构（Router → Controller → CRUD/Model），代码组织清晰易维护。
- **严格的代码规范**：前端遵循 [SoybeanJS 规范](https://docs.soybeanjs.cn/zh/standard)，集成 ESLint + oxlint + simple-git-hooks；后端使用 [Ruff](https://docs.astral.sh/ruff/) + [Pyright](https://microsoft.github.io/pyright)，保持一致的代码风格。
- **TypeScript 全覆盖**：支持严格类型检查，提升代码可维护性和开发体验。
- **丰富的主题配置**：内置多套主题方案，与 UnoCSS 深度集成，轻松定制界面风格。
- **国际化支持**：内置 vue-i18n 多语言方案（中文 / English），一键切换语言。
- **丰富的页面与组件**：内置 403、404、500 等异常页面，集成 ECharts、AntV、VChart 等可视化库，以及富文本编辑器、Markdown 编辑器等。
- **移动端适配**：响应式布局，完美支持移动端访问。
- **Docker 一键部署**：提供完整的 Docker Compose 配置（Nginx + FastAPI + Redis），一条命令即可启动全栈服务。

## 相关链接

- [在线预览](https://fast-soy-admin.sleep0.de/)
- [项目文档](https://sleep1223.github.io/fast-soy-admin-docs/zh/)
- [Apifox 接口文档](https://apifox.com/apidoc/shared-7cd78102-46eb-4701-88b1-3b49c006504b)
- [GitHub 仓库](https://github.com/sleep1223/fast-soy-admin)
- [SoybeanAdmin](https://gitee.com/honghuangdc/soybean-admin)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Tortoise ORM](https://tortoise.github.io)

## 示例图片

![](https://soybeanjs-1300612522.cos.ap-guangzhou.myqcloud.com/uPic/soybean-admin-v1-01.png)
![](https://soybeanjs-1300612522.cos.ap-guangzhou.myqcloud.com/uPic/soybean-admin-v1-02.png)

![](https://soybeanjs-1300612522.cos.ap-guangzhou.myqcloud.com/uPic/soybean-admin-v1-04.png)

![](https://soybeanjs-1300612522.cos.ap-guangzhou.myqcloud.com/uPic/soybean-admin-v1-06.png)
![](https://soybeanjs-1300612522.cos.ap-guangzhou.myqcloud.com/uPic/soybean-admin-v1-07.png)
![](https://soybeanjs-1300612522.cos.ap-guangzhou.myqcloud.com/uPic/soybean-admin-v1-08.png)

![](https://raw.githubusercontent.com/sleep1223/fast-soy-admin-docs/51832d41f1d951bd9d61a9bcfdf137deb81fd3c5/src/assets/QQ%E6%88%AA%E5%9B%BE20240517223056.jpg)
![](https://raw.githubusercontent.com/sleep1223/fast-soy-admin-docs/51832d41f1d951bd9d61a9bcfdf137deb81fd3c5/src/assets/QQ%E6%88%AA%E5%9B%BE20240517223123.jpg)

![](https://soybeanjs-1300612522.cos.ap-guangzhou.myqcloud.com/uPic/soybean-admin-v1-09.png)
![](https://soybeanjs-1300612522.cos.ap-guangzhou.myqcloud.com/uPic/soybean-admin-v1-10.png)
![](https://soybeanjs-1300612522.cos.ap-guangzhou.myqcloud.com/uPic/soybean-admin-v1-mobile.png)

## 快速开始

### 方式一：Docker 部署（推荐）

```bash
# 克隆项目
git clone https://github.com/sleep1223/fast-soy-admin
cd fast-soy-admin

# 启动全部服务
docker compose up -d

# 查看日志
docker compose logs -f        # 所有服务
docker compose logs -f app    # 仅 FastAPI
docker compose logs -f nginx  # 仅 Nginx
docker compose logs -f web    # 仅前端构建
```

更新代码后重新部署：

```bash
docker compose down && docker compose up -d
```

### 方式二：本地开发

**环境要求**

| 工具 | 版本 |
|------|------|
| Git | - |
| Python | >= 3.12 |
| Node.js | >= 20.19.0 |
| pnpm | >= 10.5.0 |

**安装与启动**

```bash
# 克隆项目
git clone https://github.com/sleep1223/fast-soy-admin
cd fast-soy-admin

# 后端依赖
uv sync  # 或 pdm install / pip install -r requirements.txt

# 前端依赖（请使用 pnpm，项目采用 pnpm monorepo 管理）
cd web && pnpm install

# 启动后端（端口 9999）
python run.py

# 启动前端（端口 9527，新开终端）
cd web && pnpm dev
```

**构建前端**

```bash
cd web && pnpm build
```

## TODO

- [x] 使用 Redis 优化响应速度
- [x] 使用 Docker 部署
- [ ] 集成 FastCRUD

## 参与贡献

欢迎提交 [Pull Request](https://github.com/sleep1223/fast-soy-admin/pulls) 或创建 [Issue](https://github.com/sleep1223/fast-soy-admin/issues/new) 来参与项目建设，任何形式的贡献都非常欢迎。

## 贡献者

感谢所有为本项目做出贡献的开发者。

<a href="https://github.com/mizhexiaoxiao">
    <img src="https://github.com/mizhexiaoxiao.png?size=120" width="64" height="64" style="border-radius:50%;" />
</a>

<a href="https://github.com/soybeanjs.png">
    <img src="https://github.com/soybeanjs.png?size=120" width="64" height="64" style="border-radius:50%;" />
</a>

<a href="https://github.com/sleep1223/fast-soy-admin/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=sleep1223/fast-soy-admin" />
</a>

## Star 趋势

[![Star History Chart](https://api.star-history.com/svg?repos=sleep1223/fast-soy-admin&type=Date)](https://star-history.com/#sleep1223/fast-soy-admin&Date)

## 开源协议

本项目基于 [MIT © 2024](./LICENSE) 协议开源，可自由使用与修改，商业使用请保留作者版权信息。作者不对软件的使用承担任何担保或责任。
