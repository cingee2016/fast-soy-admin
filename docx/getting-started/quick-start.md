# 快速开始

## 环境准备

| 工具 | 版本 |
|------|------|
| Git | - |
| Python | >= 3.12 |
| Node.js | >= 20.19.0 |
| uv | 最新 |
| pnpm | >= 10.5 |
| just | 任意版本 |

## 获取代码

```bash
git clone https://github.com/sleep1223/fast-soy-admin.git
cd fast-soy-admin
```

## 方式一：Docker 部署（推荐）

```bash
docker compose up -d postgres redis             # 首次先启动依赖服务
docker compose run --rm app uv run python -m app.cli initdb
just up                                         # == docker compose up -d
```

`initdb` 只需要在全新数据库上执行一次；后续更新如果包含模型变更，按迁移流程执行 `docker compose exec app uv run tortoise migrate`。

访问 `http://localhost:1880`，服务包括：

- **Nginx** (:1880) — 前端 + API 反向代理
- **FastAPI** (:9999) — 后端 API
- **Redis** (:6379) — 缓存

```bash
just logs      # == docker compose logs -f --tail=100
just logs app  # == docker compose logs -f --tail=100 app
just down      # == docker compose down
```

## 方式二：本地开发

```bash
just install          # 一次性安装后端 + 前端依赖
cp .env.example .env  # 复制环境变量模板，按需修改 SECRET_KEY / DB_URL / REDIS_URL 等
just db-init          # 首次初始化数据库（之后不再需要）
just run              # 并行启动后端(:9999) 和前端(:9527)，Ctrl+C 一起停
```

分开启动也可以：

```bash
just run backend   # 仅后端
just run frontend  # 仅前端
```

## 下一步

- [开发指南](./workflow.md) — 从 `just cli-init` 到完整 CRUD 模块的端到端流程
- [命令参考](../reference/commands.md) — 所有 `just` 命令与对应原始命令的对照表
- [架构](./architecture.md) — 分层结构、RBAC 权限模型
- [响应码](../reference/codes.md) — 统一业务码约定

## 项目结构

```
fast-soy-admin/
├── app/                  # 后端 (FastAPI)
│   ├── __init__.py       # App 工厂、中间件、生命周期
│   ├── core/             # 分层公共设施（CRUD、dep、中间件）
│   ├── system/           # 内置系统模块（auth / user / role / menu）
│   ├── business/         # 业务模块（autodiscover 自动加载）
│   │   └── hr/           #   示例：员工/部门/标签
│   ├── cli/              # CLI 代码生成器
│   └── utils/            # 业务开发者的统一导入入口
├── web/                  # 前端 (Vue3 + Vite + NaiveUI)
│   └── src/
│       ├── views/        # 页面组件
│       ├── service/api/  # API 请求封装
│       ├── typings/api/  # TS 类型声明
│       ├── locales/      # i18n (zh-CN / en-US)
│       ├── router/       # 动态路由（后端下发）
│       ├── store/        # Pinia
│       └── hooks/        # Vue 组合式函数
├── deploy/               # Docker / Nginx 配置
├── migrations/           # Tortoise 迁移文件
├── tests/                # 后端单元测试
├── justfile              # 所有常用命令的统一入口
└── docker-compose.yml
```

## 质量检查

```bash
just check  # 后端 + 前端所有质量检查（提交前跑）
```

细分命令：

```bash
just fmt backend         # 后端 ruff fix + format
just typecheck backend   # 后端 basedpyright
just test backend        # 后端 pytest
just lint frontend       # 前端 eslint + oxlint
just typecheck frontend  # 前端 vue-tsc
just test frontend       # 前端 vitest
```
