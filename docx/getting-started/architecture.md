# 架构

## 总览

```
                ┌──────────────────────────────────────────────┐
                │              FastAPI App                      │
                │  ┌──────────────────────────────────────┐    │
                │  │  Middleware: CORS / RequestID /      │    │
                │  │  BackgroundTask / Guard / Radar      │    │
                │  └──────────────────────────────────────┘    │
                │                                                │
                │  /api/v1/auth                  (system)        │
                │  /api/v1/route                 (system)        │
                │  /api/v1/system-manage/*       (system)        │
                │  /api/v1/business/<module>/*   (business)      │
                │                                                │
                │   api → services → controllers → models        │
                └──────────────────────────────────────────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
         Tortoise ORM           Redis             Sqids/JWT
         (SQLite/PG/MySQL)      (cache + lock)    (encode/sign)
```

## 模块边界

| 包 | 职责 | 依赖方向 |
|---|---|---|
| `app/core/` | 框架基础设施（无业务） | 不依赖 system / business |
| `app/system/` | 内置系统模块（认证、RBAC、用户、菜单、API、字典） | 仅依赖 `app/core/` |
| `app/business/<x>/` | 业务模块（HR / CRM / Inventory ...） | 依赖 `app/utils`（间接到 core/system），**不得依赖兄弟业务模块** |
| `app/utils/` | 业务开发者的统一对外入口 | 重新导出 `app/core/*` 与 `app/system/security` 等少量符号 |
| `app/cli/` | 代码生成器（init/gen/gen-web/initdb） | 仅离线使用，不参与运行时 |

任何业务模块代码**不应**出现 `from app.system.xxx import ...`（除了 system 主动暴露的 service，例如 `ensure_menu`）。需要跨业务通信请用 [事件总线](../develop/events.md)。

## 请求生命周期

1. **入站中间件**（`app/core/middlewares.py` + `make_middlewares()`）
   - `CORSMiddleware`
   - `PrettyErrorsMiddleware` — 异常输出美化
   - `BackgroundTaskMiddleware` — 把 FastAPI 的 `BackgroundTasks` 注入 `CTX_BG_TASKS`
   - `RequestIDMiddleware` — 注入 `X-Request-ID` 到响应头与 `CTX_X_REQUEST_ID`
   - `RadarMiddleware`（条件启用） — 捕获请求/SQL/异常到 Radar Dashboard
   - [`fastapi-guard`](https://fastapi-guard.com/)（条件启用） — 限流 / 自动封禁
2. **路由分发** — 业务模块路由统一前缀 `/api/v1/business/<name>`，系统模块挂在 `/api/v1/{auth,route,system-manage}` 下
3. **依赖注入**
   - `DependAuth` — JWT 解码 → 校验 token 版本号 → 加载用户与角色/按钮权限到 ContextVars
   - `DependPermission` — 在 `DependAuth` 之上，按 `role.apis` 精确比对 `(method, path)`
   - `require_buttons(...)` / `require_roles(...)` — 工厂依赖，按需挂在路由上
4. **业务逻辑**
   - `api/` 层只接线，业务规则在 `services/` 与 `controllers/`
5. **响应**
   - 一律返回 `Success` / `SuccessExtra` / `Fail`（`JSONResponse` 子类，自动 camelCase）

## 启动生命周期

```
create_app()
  ├─ register_db(app)                       # Tortoise.init(config=TORTOISE_ORM)
  ├─ register_exceptions(app)               # BizError / DoesNotExist / IntegrityError / ValidationError 处理器
  ├─ register_routers(app, prefix="/api")   # 系统模块 /api/v1/...
  ├─ discover_business_routers()            # /api/v1/business/<name>/...
  └─ setup_radar(app)                       # 可选

lifespan(app)
  ├─ init_redis() → app.state.redis
  ├─ FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
  ├─ delete _INIT_LOCK_KEY / _INIT_DONE_KEY
  ├─ _run_init_data(app)               # 多 worker 中仅 leader 执行
  │    ├─ init_menus()                 # 系统菜单种子（仅在 Menu 表为空时插入）
  │    ├─ refresh_api_list()           # FastAPI 路由 ↔ Api 表全量对账
  │    ├─ init_users()                 # 系统角色 + 默认账号 + 字典
  │    ├─ for each business init():    # 业务模块 init_data.init()
  │    └─ refresh_all_cache()          # 角色权限 / 常量路由刷到 Redis
  ├─ startup_radar()                   # 可选
  └─ yield
       ↓ shutdown
  └─ close_redis()
```

详细同步语义见 [启动初始化与对账](../develop/init-data.md)。

## RBAC 数据模型

```
User ←M2M→ Role ←M2M→ Menu      (菜单权限：决定前端可见的路由)
                ←M2M→ Button    (按钮权限：决定页面内可执行的操作)
                ←M2M→ Api       (接口权限：决定可调用的后端接口)
                FK    Menu      (角色首页 by_role_home)
              field   data_scope (行级数据范围: all / department / self / custom)
```

- 超级管理员 `R_SUPER`（[`app.core.constants.SUPER_ADMIN_ROLE`](../../../app/core/constants.py)）跳过所有权限校验
- API 权限由 `refresh_api_list()` 自动维护（按 `(method, path)` 全量对账）
- 菜单/按钮由各模块 `init_data.py` 通过 `ensure_menu()` 声明，可选 `reconcile_menu_subtree()` 做 IaC 对账
- 按钮编码约定 `B_<MODULE>_<RESOURCE>_<ACTION>`（如 `B_HR_EMP_CREATE`）
- 详见 [认证与权限](../develop/auth.md) / [数据权限](../develop/data-scope.md)

## 多 worker 启动

生产环境通常用 4 个 granian worker。启动时通过 Redis 分布式锁 `app:init_lock` 协调：

- Leader（`SET app:init_lock 1 NX EX 120` 成功者）执行完整 init，然后 `SET app:init_done 1 EX 120`
- 其他 worker 轮询 `app:init_done`，最长等 150s 后即使没等到也启动
- 每次进程启动前 leader 先 `DEL` 锁，因此每次重启都会真的跑一次 init

## 多数据库连接

- 默认所有模型挂在主连接 `conn_system`
- 业务模块在自己的 `config.py` 声明独立 `DB_URL` 时，autodiscover 会注册独立连接 `conn_<biz>` 与独立 app
- 跨模型事务用 `get_db_conn(Model)` 取连接名，不要硬编码
- 详见 [切换数据库](../ops/database.md#业务模块独立数据库进阶)

## 缓存模型

| 数据 | Redis Key | TTL | 谁写 |
|---|---|---|---|
| 常量路由 | `constant_routes` | 永久 | `refresh_all_cache` |
| 角色菜单 ID | `role:{code}:menus` | 永久 | `load_role_permissions` |
| 角色 API | `role:{code}:apis` | 永久 | 同上 |
| 角色按钮 | `role:{code}:buttons` | 永久 | 同上 |
| 角色数据范围 | `role:{code}:data_scope` | 永久 | 同上 |
| 用户角色 | `user:{uid}:roles` | 永久 | `load_user_roles` |
| 用户首页 | `user:{uid}:role_home` | 永久 | 同上 |
| Token 版本 | `token_version:{uid}` | 永久 | 修改密码 / 模拟登录 |
| 业务自有缓存 | 按模块自定义 | 模块自定 | 模块自定 |

详见 [缓存](../ops/cache.md)。

## 接下来读什么

- [核心机制 / CRUDRouter](../develop/crud-router.md)
- [核心机制 / Schema 基类](../develop/schema.md)
- [认证与权限](../develop/auth.md)
- [启动初始化与对账](../develop/init-data.md)
