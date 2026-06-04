# FastSoyAdmin - Claude Code Guide

FastSoyAdmin v1.0.0 | FastAPI + Vue3 全栈后台管理模板 | MIT

后端 [app/](app/)（FastAPI/Python），前端 [web/](web/)（Vue3/TypeScript，pnpm workspace），部署 [deploy/](deploy/)，迁移 [migrations/](migrations/)。

文档（**所有约定细节看这里，本文不再重复**）：
- 在线：https://sleep1223.github.io/fast-soy-admin-docs/
- 离线：[docx/](docx/) — 与在线一致的 Markdown 镜像
- 项目说明：[README.md](README.md) / [docx/](docx/)

---

## 重要文件（动手前先看）

- **[.env](.env)** — 运行配置事实来源（`SECRET_KEY` / `DB_URL` / `REDIS_URL` / `JWT_*`）。从 [.env.example](.env.example) 复制；**不要**提交。
- **[justfile](justfile)** — 所有常用命令入口。`just --list` 列全部；不要绕过它直调底层命令。
- **[app/core/](app/core/)** — 框架级代码，影响整个后端。改这里前读 [init_app.py](app/core/init_app.py)、[base_schema.py](app/core/base_schema.py)、[crud.py](app/core/crud.py)、[router.py](app/core/router.py)。
- **[app/utils/__init__.py](app/utils/__init__.py)** — 业务模块统一 import 入口；新增 core 能力要给 business 用必须在这里 re-export。
- **[app/system/services/init_helper.py](app/system/services/init_helper.py)** — `ensure_menu` / `ensure_role` / `reconcile_menu_subtree` / `refresh_api_list`。**业务模块允许从这里 import**，是少数显式暴露的 system service。
- **`DB_URL` 指向的数据库** — 默认依赖含 `tortoise-orm[asyncpg]` + `aiosqlite`，PostgreSQL/SQLite 开箱即用；切 MySQL/MSSQL/Oracle 需 `uv sync --extra {mysql|mssql|oracle}`。**不要**直接 SQL 改它绕过模型/迁移；走 `just mm`。

**Python 工具链** — 后端依赖与脚本一律走 `uv`：`uv sync` / `uv add <pkg>` / `uv run <cmd>`。**不要**直接调 `python` / `pip` / `python -m xxx`，**不要**用系统/pyenv 的 `python`。

> **Trust by verify**：真实状态有时与配置/代码漂移（手工迁移、未跑 `mm`、Redis 缓存未刷新）。动手前用 `just dbhistory`、读 `.env`、看 Redis key、跑 `just check` 核对一遍。

---

## 标准操作流程

### 任何修改之前

1. **明确范围**：system 还是 business？哪个模块？影响哪些表 / 路由 / 角色？
2. **看清现状**：`git status`、`just dbhistory`、读相关 `models.py` / `init_data.py`
3. **跟规范对齐**：[强制约定清单](#强制约定清单pr-review-checklist) + [docx/standard/](docx/standard/)
4. **小步推进**：先生成迁移看 SQL 再 apply；改 schema 先单元测试

### 常用命令

```bash
just install                          # 装后端 (uv sync) + 前端 (pnpm install)
cp .env.example .env                  # 首次复制环境变量
just db-init                          # 首次初始化数据库

just run                              # 并行启动后端 :9999 + 前端 :9527
just run backend / just run frontend  # 仅后端 / 仅前端

just mm                               # makemigrations + migrate（启动不会自动迁移）
just check                            # 提交前必跑：ruff + basedpyright + pytest + eslint + oxlint + vue-tsc
just up / just logs / just down       # docker compose
```

完整命令清单见 [docx/reference/commands.md](docx/reference/commands.md)。

### 新增业务模块

```bash
just cli-init <name>              # 生成骨架
# 编辑 app/business/<name>/models.py 定义模型
just cli-gen-all <name> <中文名>  # 生成后端 + 前端 CRUD
just mm && just run && just check
```

业务模块结构、autodiscover 约定见 [docx/develop/autodiscover.md](docx/develop/autodiscover.md)。

### 启动初始化与对账

每次启动由 Redis leader worker 串行执行：`init_menus()` → `refresh_api_list()` → `init_users()` → 各业务模块 `init_data.init()` → `refresh_all_cache()`。

⚠️ **IaC 模式陷阱**：启用了 `reconcile_menu_subtree(...)` 的子树是单一数据源，通过 Web UI 在该子树下手工创建的菜单/按钮**会在下次重启时被清除**。允许用户动态创建菜单的子树**不要**调用它。

⚠️ **漂移告警**：`ensure_role` 引用的 `route_name` / `button_code` / `(method, path)` 解析失败会 `log.warning`——必须立即修复，否则角色权限静默缺失。

完整说明见 [docx/develop/init-data.md](docx/develop/init-data.md)。

### 事故响应

1. **先读日志**：`docker compose logs -f`、Radar 面板（`/manage/radar/*`）、[app/core/exceptions.py](app/core/exceptions.py) 业务码
2. **看 Redis 状态**：leader worker key、缓存 key、限流 key
3. **未确认前不动数据**：尤其是 truncate / drop / 反向迁移 / 直接改数据库文件
4. **建议恢复方案再执行**：先汇报、给选项、等用户拍板

---

## 权限边界

### 始终允许（无需确认）

- 读取仓库文件、`.env.example`、`justfile`、`pyproject.toml`、`web/package.json`
- 跑只读 / `--check` / dry-run 命令
- `just --list` / `just dbhistory` / `just fmt backend` / `just typecheck backend` / `just test backend` / `just check` / `just typecheck frontend`
- 查看监控、日志、Radar 面板
- 读取系统表 / 元数据：`information_schema.*`、Tortoise meta

### 需要用户确认（先问再做）

- **框架级**：编辑 `app/core/*`、`app/utils/__init__.py` 的对外 re-export、`init_app.py` 全局中间件/异常处理器/路由挂载、`app/core/code.py` 已有响应码（追加新码不需要确认）、`justfile` 已有 target 语义、`pyproject.toml` / `web/package.json` 主版本依赖升级
- **数据库**：`migrate`（先给用户看 SQL）、手写迁移文件、改 `BaseModel` / `AuditMixin` / `SoftDeleteMixin` / `TreeMixin`
- **RBAC / 安全**：改 `init_data.py` 菜单/按钮/角色种子、`R_SUPER` 行为或 `DependPermission` 校验逻辑、`app/core/data_scope.py` 行级规则、`JWT_*` / `GUARD_*` / `CORS_ORIGINS`
- **部署 / 服务**：改 `deploy/`、`docker-compose.yml`、`nginx.conf`，重启服务、`just up` / `just down`

### 禁止 — 始终需要明确授权

破坏性操作必须用户明确说"确认/yes"：

```
- DROP DATABASE / DROP TABLE / TRUNCATE / DELETE 不带 WHERE
- 反向迁移 / 手工 downgrade
- rm -rf migrations/ / rm app_system.sqlite3
- git reset --hard / git push --force（非个人 feature 分支）
- 删除业务模块目录 app/business/<name>/
- 直接 SQL 改用户/角色/权限表绕过 init_data
- 清空 Redis（FLUSHDB / FLUSHALL）
```

**业务数据访问限制**：默认**不读业务表内容**；排查问题前问授权；即便授权也用 `LIMIT` + 指定列；不要把业务数据写到日志 / 临时文件。

**确认流程**：操作的具体表 / 模块 / 文件？有没有近期备份？让用户输入完整名字确认（如 `truncate biz_hr_employee` 让用户键入 `biz_hr_employee`）。

---

## 架构速览

两个顶层包：[app/system/](app/system/)（认证/RBAC/用户/角色/菜单/API/字典/监控）+ [app/business/<name>/](app/business/)（业务，启动时 [autodiscover.py](app/core/autodiscover.py) 自动发现）。每个模块统一分层：`api/` → `services/` → `controllers/` → `models + schemas`。

**依赖方向**（铁律）：
- `app/core/` 不依赖 system / business
- `app/system/` 仅依赖 `app/core/`
- `app/business/<x>/` 依赖 `app/utils`，**不得**反向 import `app.system.*`（白名单：`init_helper` 显式暴露的 service），**不得**互相 import 兄弟业务模块——跨模块走事件总线（`emit` / `on`）

**前端**：Vue3 + Vite + Naive UI + Elegant Router + Pinia + UnoCSS + Alova。

完整架构、分层职责、关键 core 文件清单见 [docx/getting-started/architecture.md](docx/getting-started/architecture.md) 与 [docx/develop/intro.md](docx/develop/intro.md)。

---

## 强制约定清单（PR review checklist）

> 各项展开见 [docx/develop/](docx/develop/) 与 [docx/standard/](docx/standard/)。

1. 必须用 `Success` / `SuccessExtra` / `Fail`；不返回裸 dict、不手拼 snake_case
2. 业务 schema 继承 `SchemaBase`；分页继承 `PageQueryBase`；ID 用 `SqidId`/`SqidPath`；整型用 `Int16/32/64`；Update schema 用 `make_optional`
3. 标准 6 路由必须 `CRUDRouter`；自定义用 `@crud.override`；不要绕过 `_OrderedRouter`
4. `controllers` / `services` 不要 import `fastapi.Request` / `Response`
5. 写接口必须挂按钮权限；业务角色种子必须显式 `data_scope`（`all` / `department` / `self` / `custom`）
6. 不要靠"前端隐藏按钮"做安全；不要在业务里直接判 `role_code == "..."`（用 `has_role_code` / `has_button_code`）
7. 模型继承 `BaseModel + AuditMixin`；文件头 `# pyright: reportIncompatibleVariableOverride=false`；字段加 `description="..."`；类 docstring 写中文名；`Meta.table = biz_<module>_<entity>`；**每个 `ForeignKeyField` / `OneToOneField` 上方显式声明 `<name>_id: int`（或 `int | None`）注解**；创建/更新/比较一律用 `obj.<name>_id`；访问关系对象字段必须先 `prefetch_related(...)` 或 `await obj.<name>`
8. 业务模块 import 入口统一 `from app.utils import ...`
9. 跨业务模块联动用事件总线（`emit` / `on`），不要直接 import 兄弟模块
10. 事务用 `in_transaction(get_db_conn(Model))`；**不要**硬编码连接名；事务内**不要**做 HTTP / Redis / 队列
11. 不要 `raise HTTPException`；用 `BizError` / `SchemaValidationError`（**不是** `ValueError`）
12. 业务自有缓存按 `<module>_<resource>:<scope>` 命名，读 → miss → 查 → 写 TTL，变更时主动失效；不要给分页接口加全局 `@cache(...)`
13. 关键节点 / 权限拒绝用 `radar_log(...)`；高频调试 `log.debug`；不要 `print(...)`
14. 所有函数加类型注解；`just check` 必须全绿
15. **`@crud.override` 内禁止**：`in_transaction(...)` / `request.app.state.redis` / 跨模型写（含 `m2m.add` / `m2m.clear`）/ 调其他模块 service / 发事件 / 写审计——这些必须下沉到 `services/`
16. **CRUDRouter 适用边界**：仅给贫血资源用（字典/标签/部门/分类）。聚合根（用户/角色/订单/工单等带状态、副作用）用显式 `@router.post(...)` + `services/`。判断条件：override ≥ 3、override 内出现事务/Redis/跨模型写、资源是聚合根或带状态机、写操作有副作用（通知/审计/事件/失效缓存）——任一命中立即改写

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **fast-soy-admin** (8509 symbols, 14093 relationships, 300 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/fast-soy-admin/context` | Codebase overview, check index freshness |
| `gitnexus://repo/fast-soy-admin/clusters` | All functional areas |
| `gitnexus://repo/fast-soy-admin/processes` | All execution flows |
| `gitnexus://repo/fast-soy-admin/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
