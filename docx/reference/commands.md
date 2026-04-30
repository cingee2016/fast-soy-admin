# 命令参考

常用命令封装在根目录 `Makefile`。运行 `make` 列出所有命令：

```bash
make          # 等同于 make help
make help
```

> **说明**：`MOD=xxx` 表示需要传入模块名的位置参数，例如 `make cli-init MOD=inventory`。

## 后端（Backend）

| 原始命令 | Make 命令 | 作用 |
|---|---|---|
| `uv sync` | `make install` | 安装后端依赖 |
| `uv run python run.py` | `make run` | 启动后端开发服务器（:9999） |
| `uv run ruff check app/`<br>`uv run ruff format --check app/` | `make lint` | Ruff 代码检查（不修改） |
| `uv run ruff check --fix app/`<br>`uv run ruff format app/` | `make fmt` | Ruff 自动修复 + 格式化 |
| `uv run basedpyright app` | `make typecheck` | 静态类型检查 |
| `uv run pytest tests/ -v` | `make test` | 运行单元测试 |
| — | `make check` | 一键跑完 fmt + typecheck + test |

## 数据库（Database）

| 原始命令 | Make 命令 | 作用 |
|---|---|---|
| `uv run python -m app.cli initdb` | `make initdb` | 首次初始化数据库（建表 + 基础数据） |
| `uv run tortoise makemigrations` | `make makemigrations` | 根据模型变更生成迁移文件 |
| `uv run tortoise migrate` | `make migrate` | 应用所有未执行的迁移 |
| — | `make mm` | 一键生成并应用迁移（makemigrations + migrate 的缩写） |
| `uv run tortoise history` | `make dbhistory` | 查看迁移历史 |

## CLI 代码生成（Code Generation）

| 原始命令 | Make 命令 | 作用 |
|---|---|---|
| `uv run python -m app.cli init <MOD>` | `make cli-init MOD=xxx` | 创建业务模块骨架（只含 `models.py`） |
| `uv run python -m app.cli gen <MOD>` | `make cli-gen MOD=xxx` | 解析 `models.py`，生成后端 schemas/controllers/api 等 |
| `uv run python -m app.cli gen-web <MOD>` | `make cli-gen-web MOD=xxx [CN=中文名]` | 解析 `models.py`，生成前端 service/typings/views/i18n（自动合并到 `_generated/<mod>/`，无需手动改 `zh-cn.ts` / `app.d.ts`） |
| — | `make cli-gen-all MOD=xxx [CN=中文名]` | 一次跑完 cli-gen + cli-gen-web |

详细使用流程见 [开发指南](../getting-started/workflow.md)。

## 前端（Frontend）

| 原始命令 | Make 命令 | 作用 |
|---|---|---|
| `cd web && pnpm install` | `make web-install` | 安装前端依赖 |
| `cd web && pnpm dev` | `make web-dev` | 启动前端开发服务器（:9527） |
| `cd web && pnpm build` | `make web-build` | 生产构建前端 |
| `cd web && pnpm lint` | `make web-lint` | ESLint + oxlint |
| `cd web && pnpm typecheck` | `make web-typecheck` | vue-tsc 类型检查 |
| — | `make web-check` | 一键跑完 web-lint + web-typecheck |

## 全栈（Full Stack）

| 命令 | 作用 |
|---|---|
| `make install-all` | 同时安装后端 + 前端依赖 |
| `make dev` | 同时启动后端（:9999）和前端（:9527），按 `Ctrl+C` 一起停 |
| `make check-all` | 同时跑后端和前端的所有质量检查 |

## Docker

| 原始命令 | Make 命令 | 作用 |
|---|---|---|
| `docker compose up -d` | `make up` | 启动全栈（nginx :1880 + fastapi :9999 + redis） |
| `docker compose up -d --build` | `make rebuild` | 重建镜像并重建容器（代码 / Dockerfile 变更后使用） |
| `docker compose down` | `make down` | 停止并移除容器 |
| `docker compose logs -f` | `make logs` | 实时查看所有服务日志，可选 `SVC=app\|nginx\|redis` 过滤、`TAIL=N` 指定行数 |

## 典型开发流程

新业务模块开发流程：

```bash
# 1. 装依赖（仅首次）
make install-all

# 2. 复制环境变量模板，按需修改 SECRET_KEY / DB_URL / REDIS_URL 等（仅首次）
cp .env.example .env

# 3. 首次初始化数据库（仅首次）
make initdb

# 4. 创建业务模块骨架
make cli-init MOD=inventory

# 5. 编辑 app/business/inventory/models.py，定义 Tortoise 模型

# 6. 生成后端代码（schemas / controllers / api / init_data）
make cli-gen MOD=inventory

# 7. 生成前端代码（service / typings / views / i18n 片段）
make cli-gen-web MOD=inventory CN=库存管理

# 6+7 也可一次跑完:
# make cli-gen-all MOD=inventory CN=库存管理

# 8. 执行数据库迁移
make mm

# 9. 启动前后端开发服务器
make dev

# 10. 提交前跑一遍质量检查
make check-all
```
