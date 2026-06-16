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
| `uv run python -m app.cli gen <MOD>` | `just cli-gen xxx` | 选择 CRUD 模型、模糊/精确查询字段，生成后端 schemas/controllers/api 等 |
| `uv run python -m app.cli gen-web <MOD>` | `just cli-gen-web xxx [中文名]` | 选择页面模型、列表/搜索字段，生成前端 service/typings/views/i18n |
| `uv run python -m app.cli gen-all <MOD>` | `just cli-gen-all xxx [中文名]` | 一次选择并生成后端 + 前端 CRUD |
| `uv run python -m app.cli crud <MOD>` | `just cli-crud xxx [中文名]` | 同上，完整 CRUD 生成别名 |

### 参数化生成（AI 友好）

所有生成命令都支持 `-h/--help` 查看完整参数。需要无交互生成时加 `--yes`：

```bash
uv run python -m app.cli crud utility_fee --cn-name 水电费 --yes --force
```

生成前可加 `--dry-run` 预览将创建、覆盖或追加的文件；dry-run 不写磁盘，也不要求当前 Git 工作区干净：

```bash
just cli-crud inventory 库存管理 "--yes --dry-run"
```

选择模型与字段时统一使用 `Model:field1,field2`，多个模型可重复参数或用分号分隔：

```bash
uv run python -m app.cli crud utility_fee \
  --cn-name 水电费 \
  --models UtilityConfig,UtilityBill \
  --contains UtilityConfig:name,remark \
  --exact UtilityConfig:enabled \
  --list-fields UtilityBill:room_id,billing_date,total_amount,status \
  --search-fields UtilityBill:room_id,billing_date,status
```

后端高级能力也可直接从 CLI 调用：

```bash
uv run python -m app.cli crud hr \
  --cn-name 人事 \
  --models Employee,Department \
  --data-scope Employee:user_id,tenant_id \
  --button-auth \
  --soft-delete Employee \
  --tree Department \
  --list-order Employee:-created_at,id \
  --enable-routes Department:list,get \
  --list-cache Department:60 \
  --rate-limit Employee:30/60
```

能力说明：

| 参数 | 生成效果 |
|---|---|
| `--data-scope Model:user_id,scope_id` | 覆盖列表接口并拼接 `build_scope_filter()`；业务范围 ID 取值会生成 `_get_scope_id()` 钩子 |
| `--button-auth` | 生成菜单按钮声明，并在 create/edit/delete/batch_delete 挂 `require_buttons()` |
| `--soft-delete Model` | `CRUDRouter(..., soft_delete=True)`，模型需使用 `SoftDeleteMixin` |
| `--tree Model` | `CRUDRouter(..., tree_endpoint=True)`，模型需使用 `TreeMixin` 或 `parent_id` |
| `--list-cache Model:60` | 为列表 override 加 `@cache(expire=60, namespace=...)`，仅建议低组合度列表使用 |
| `--rate-limit Model:30/60` | 在 `api/manage.py` 输出 `ENDPOINT_RATE_LIMITS`，启动时自动合并到 guard 配置 |
| `--enable-routes Model:list,get` | 限制标准 CRUD 路由集合 |
| `--exclude-fields Model:secret` | 设置 `to_dict()` 排除字段 |

`just` 包装命令可通过最后一个参数透传 CLI 参数，例如：

```bash
just cli-crud utility_fee 水电费 "--yes --models UtilityConfig --button-auth"
```

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
# just cli-crud inventory 库存管理

# 8. 执行数据库迁移
just mm

# 9. 启动前后端开发服务器
just run

# 10. 提交前跑一遍质量检查
just check
```
