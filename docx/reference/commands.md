# 命令参考

常用命令封装在根目录 `justfile`。运行 `just` 列出所有命令：

```bash
just --list
```

> **说明**：`xxx` 表示位置参数，例如 `just cli-init inventory`。

## 后端（Backend）

| 原始命令 | just 命令 | 作用 |
|---|---|---|
| `uv sync` | `just install backend` | 安装后端依赖 |
| `uv run python run.py` | `just run backend` | 启动后端开发服务器（:9999） |
| `uv run ruff check app/`<br>`uv run ruff format --check app/` | `just lint backend` | Ruff 代码检查（不修改） |
| `uv run ruff check --fix app/`<br>`uv run ruff format app/` | `just fmt backend` | Ruff 自动修复 + 格式化 |
| `uv run basedpyright app` | `just typecheck backend` | 静态类型检查 |
| `uv run pytest tests/ -v` | `just test backend` | 运行单元测试 |
| — | `just check backend` | 一键跑完 fmt + typecheck + test |

## 数据库（Database）

| 原始命令 | just 命令 | 作用 |
|---|---|---|
| `uv run python -m app.cli initdb` | `just db-init` | 首次初始化数据库（建表 + 基础数据） |
| `uv run python -m app.cli initdb --force` | `just db-reset` | 清空当前开发库和本地迁移基线后重新初始化 |
| `uv run tortoise makemigrations` | `just makemigrations` | 根据模型变更生成迁移文件 |
| `uv run tortoise migrate` | `just migrate` | 应用所有未执行的迁移 |
| — | `just mm` | 一键生成并应用迁移（makemigrations + migrate 的缩写） |
| `uv run tortoise history` | `just dbhistory` | 查看迁移历史 |

## CLI 代码生成（Code Generation）

| 原始命令 | just 命令 | 作用 |
|---|---|---|
| `uv run python -m app.cli init <MOD>` | `just cli-init xxx` | 创建业务模块骨架（只含 `models.py`） |
| `uv run python -m app.cli gen <MOD>` | `just cli-gen xxx` | 解析 `models.py`，生成后端 schemas/controllers/api 等 |
| `uv run python -m app.cli gen-web <MOD>` | `just cli-gen-web xxx [中文名]` | 解析 `models.py`，生成前端 service/typings/views/i18n（自动合并到 `_generated/<mod>/`，无需手动改 `zh-cn.ts` / `app.d.ts`） |
| — | `just cli-gen-all xxx [中文名]` | 一次跑完 cli-gen + cli-gen-web |

详细使用流程见 [开发指南](../getting-started/workflow.md)。

## 前端（Frontend）

| 原始命令 | just 命令 | 作用 |
|---|---|---|
| `cd web && pnpm install` | `just install frontend` | 安装前端依赖 |
| `cd web && pnpm dev` | `just run frontend` | 启动前端开发服务器（:9527） |
| `cd web && pnpm exec oxlint`<br>`cd web && pnpm exec eslint .` | `just lint frontend` | 前端代码检查（不修改） |
| `cd web && pnpm lint`<br>`cd web && pnpm fmt` | `just fmt frontend` | 前端自动修复 + 格式化 |
| `cd web && pnpm typecheck` | `just typecheck frontend` | vue-tsc 类型检查 |
| `cd web && pnpm test` | `just test frontend` | Vitest 单元测试 |
| `cd web && pnpm build` | `just build frontend` / `just build` | 生产构建前端 |
| — | `just check frontend` | 一键跑完 fmt + typecheck + test |

## 全栈（Full Stack）

| 命令 | 作用 |
|---|---|
| `just install` | 同时安装后端 + 前端依赖 |
| `just run` | 同时启动后端（:9999）和前端（:9527），按 `Ctrl+C` 一起停 |
| `just fmt` | 同时格式化 / 修复后端 + 前端代码 |
| `just test` | 同时运行后端 + 前端测试 |
| `just check` | 同时跑后端和前端的所有质量检查 |

兼容别名仍可使用：`just install-all`、`just check-all`、`just web-install`、`just web-dev`、`just web-build`、`just web-lint`、`just web-typecheck`、`just web-check`。

## Docker

| 原始命令 | just 命令 | 作用 |
|---|---|---|
| `docker compose up -d` | `just up` | 启动全栈（nginx :1880 + fastapi :9999 + redis） |
| `docker compose up -d --build` | `just rebuild` | 重建镜像并重建容器（代码 / Dockerfile 变更后使用） |
| `docker compose down` | `just down` | 停止并移除容器 |
| `docker compose logs -f` | `just logs` | 实时查看所有服务日志，可用 `just logs app` 过滤服务，`just logs app 200` 指定行数 |

## 典型开发流程

新业务模块开发流程：

```bash
# 1. 装依赖（仅首次）
just install

# 2. 复制环境变量模板，按需修改 SECRET_KEY / DB_URL / REDIS_URL 等（仅首次）
cp .env.example .env

# 3. 首次初始化数据库（仅首次）
just db-init

# 4. 创建业务模块骨架
just cli-init inventory

# 5. 编辑 app/business/inventory/models.py，定义 Tortoise 模型

# 6. 生成后端代码（schemas / controllers / api / init_data）
just cli-gen inventory

# 7. 生成前端代码（service / typings / views / i18n 片段）
just cli-gen-web inventory 库存管理

# 6+7 也可一次跑完:
# just cli-gen-all inventory 库存管理

# 8. 执行数据库迁移
just mm

# 9. 启动前后端开发服务器
just run

# 10. 提交前跑一遍质量检查
just check
```
