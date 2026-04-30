# 常见问题

按场景分类。前端运行 / 后端运行 / 模块开发 / 权限 / 部署。

## 启动 & 安装

### `python run.py` 报 "no such table"

启动时**不会**自动建表 / 迁移。首次必须：

```bash
make initdb        # 等同 tortoise init-db + 首次种子数据
# 或
make mm            # makemigrations + migrate
```

后续模型变更也走 `make mm`。详见 [命令参考](../reference/commands.md)。

### Redis 连接失败

```
redis-cli ping     # 应返回 PONG
```

或临时用本地 Redis：

```dotenv
REDIS_URL=redis://localhost:6379/0
```

### 端口被占用

后端 9999 / 前端 9527 / Nginx 1880。改 `run.py` 或 `web/vite.config.ts` 即可。

## 模块开发

### 重启后我手动建的菜单 / 按钮被清掉了

`init_data.py` 调用了 [`reconcile_menu_subtree(...)`](../develop/init-data.md#菜单按钮对账reconcile_menu_subtree) — 该子树进入 IaC 模式，**只接受**通过 `init_data.py` 声明的菜单 / 按钮，Web UI 手动创建的会在下次启动时被删除。

某子树需允许动态创建菜单时，**不要**对它调 `reconcile_menu_subtree`。

### 启动日志报 `ensure_role 'XXX': missing apis [...]`

声明的 `(method, path)` 在 `Api` 表里找不到对应路由——通常因为：

- 路由被重命名 / 删除，但角色 seed 的 `apis` 列表忘了同步
- 拼写错误（注意 method 是小写：`"post"` 不是 `"POST"`）

**看到必须修**——否则该角色的对应权限会静默缺失。详见 [启动初始化与对账](../develop/init-data.md#ensure_role-配置漂移告警)。

### 删了 init_data 里的角色，DB 中的 Role 还在

`ensure_role` 是 upsert，**不会自动删** init_data 中已删除的角色。删除走数据库迁移：

```python
# migrations/app_system/
async def upgrade(db):
    await db.execute_query("DELETE FROM roles WHERE role_code = 'R_OLD'")
```

业务种子数据同理，刻意不自动化。详见 [启动初始化与对账](../develop/init-data.md#删除残留的手动清理)。

### 业务模块新加的，但路由没挂

启动日志会有提示。常见原因：

```
Business: module 'inventory' discovered but has no api.py or api/ package — routes will not be registered
```

补 `api/__init__.py` 并 `export router: APIRouter`。

```
Business: module 'inventory' api module does not export a valid 'router' (APIRouter) object
```

`api/__init__.py` 必须有 `router = APIRouter()` 这一行。详见 [自动发现](../develop/autodiscover.md#常见漂移与排查)。

### 想临时屏蔽某个业务模块

```bash
mv app/business/inventory app/business/_inventory
```

`autodiscover` 会跳过 `_` 开头的目录。

### CLI 生成的代码里 `// TODO`

外键 / 自定义枚举的下拉数据源无法自动推导。搜全工程 TODO，补齐 `options` 的数据源（一般是 `fetchGetXxxList` 请求）。

## 权限

### 改了角色 / 菜单后用户没刷出权限

权限走 Redis 缓存。CUD 后**主动**刷新：

```python
from app.core.cache import load_role_permissions, load_user_roles

await load_role_permissions(redis, role_code="R_HR_ADMIN")
await load_user_roles(redis, user_id=123)
```

或者直接重启（启动时 `refresh_all_cache` 会全量加载）。

### 用户被踢但 token 还能用

修改密码 / 强制下线后调：

```python
from app.system.services.auth import invalidate_user_session
await invalidate_user_session(redis, user_id)
```

会 `INCR token_version:{uid}`，旧 token 在下一次请求时返回 `2106 SESSION_INVALIDATED`。详见 [认证](../develop/auth.md#token-失效token_version)。

### 业务接口权限拒绝（`2201`）但角色已挂菜单

菜单和 API 是**两个不同**的权限维度。角色 seed 必须**同时**给 `menus` 和 `apis`：

```python
await ensure_role(
    role_code="R_HR_ADMIN",
    menus=[..., "hr_employee"],
    apis=[
        ("post", "/api/v1/business/hr/employees/search"),
        ("post", "/api/v1/business/hr/employees"),
        ...
    ],
)
```

### 部门主管看到了全公司的数据

种子里**没有**显式声明 `data_scope`。模型默认 `all` = 全可见。

```python
{
    "role_code": "R_DEPT_MGR",
    "data_scope": DataScopeType.department,    # ← 必须显式
    ...
}
```

详见 [数据权限](../develop/data-scope.md)。

## 路由（前端）

### 修改 `.env` 不生效

需要重启 Vite 开发服务器。

### 路由不在菜单中显示

检查菜单 `hide_in_menu=True`，或后端没把该 `route_name` 加到当前角色的 `menus`。

### 静态路由 vs 动态路由

- `VITE_AUTH_ROUTE_MODE=static` — 前端自定义路由，靠 `roles` meta 过滤
- `VITE_AUTH_ROUTE_MODE=dynamic`（默认） — 后端按角色下发路由，调 `GET /api/v1/route/user-routes`

### 跨域错误

开发环境用 Vite 代理（`vite.config.ts` 的 `server.proxy`），生产环境用 Nginx 反代（详见 [部署](../ops/deployment.md)）。

### 生产 404

确保 Nginx 配置了 `try_files $uri $uri/ /index.html;`，否则刷新内层路由会 404。

### Vue "多根元素" 报错

`<Transition>` 切换页面动画依赖单根元素：

```vue
<template>
  <div>...</div>     <!-- ✅ 单根 -->
</template>

<template>
  <div>...</div>
  <div>...</div>     <!-- ❌ 多根 -->
</template>
```

## API ID

### 前端拿到的 ID 是字符串 `Yc7vN3kE`，不是数字

那是 [sqid](../develop/sqids.md) — 对外暴露的资源 ID 一律走 sqid。前端无需解码，原样发回后端即可（后端用 `SqidPath` / `SqidId` 自动解码）。

### 测试里发数字 ID 也通过了？

兼容期允许：`SqidId` 的 `_sqid_to_int` 同时接受 int / 数字字符串 / sqid 三种形式。迁移完成后可在源码中收紧。

### 部署后所有外部 sqid 链接都失效

`SECRET_KEY` 被换了——sqid 字母表由 SECRET_KEY 派生。详见 [Sqids / 轮换 SECRET_KEY](../develop/sqids.md#轮换-secret_key-怎么办)。

## 部署

### 容器里所有请求都被 guard 误封

部署在 Nginx 之后没开反代头还原，所有请求看起来都来自 nginx 容器 IP。修复：

```dotenv
PROXY_HEADERS_ENABLED=true
TRUSTED_HOSTS=["10.0.0.0/8"]   # 信任的上游
```

### 怎么让某 IP 不被 guard 封

```bash
redis-cli --scan --pattern "fastapi_guard:*" | xargs redis-cli del
```

或临时 `GUARD_ENABLED=false` 重启。

### 切换数据库后启动报 "module not found: asyncpg"

主库引擎没装对应驱动：

```bash
uv add asyncpg          # postgres
uv add asyncmy          # mysql
uv add asyncodbc        # mssql
```

详见 [切换数据库 / 驱动安装](../ops/database.md#驱动安装)。

### 多 worker 启动后菜单 / 用户重复创建？

不会。`_run_init_data` 通过 Redis 锁 `app:init_lock` 选 leader，只有 leader 跑 init。

```bash
redis-cli get app:init_done    # 应该是 "1"
```

## Docker

### 查看后端日志

```bash
make logs                        # 全部
make logs SVC=app                # 仅后端；SVC=nginx|redis 同理，TAIL=N 指定行数
docker compose logs -f app       # 等价的原生写法
```

### 更新部署

```bash
git pull
make down && make up
```

### 容器内时区不对

Tortoise `use_tz=False, timezone=Asia/Shanghai`。如需 UTC 全局：在 `app/core/config.py` 改 `TORTOISE_ORM["use_tz"]=True`，并把 `timezone` 改成 `UTC`。
