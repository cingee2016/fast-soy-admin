# 缓存

后端有三类缓存场景：

| 场景 | 工具 | 何时刷新 |
|---|---|---|
| 系统级"权限热数据"（角色权限、常量路由、token 版本） | [`app/core/cache.py`](../../../app/core/cache.py) 的专用函数 | 启动 `refresh_all_cache` + CUD 时增量调用 |
| 业务接口级"每次返回结果" | `fastapi-cache2` 装饰器 | TTL 到期 |
| 业务模块自有"小热点"（字典选项、统计） | 模块自带的 `cache_utils.py` + 直接读写 Redis | 业务变更时主动失效 |

底层 Redis 客户端在 `app.state.redis`（`redis.asyncio.Redis`），通过 `request.app.state.redis` 取用。

## 系统级权限缓存

`app/core/cache.py` 维护以下 key：

| Key | 内容 | 写入方 |
|---|---|---|
| `constant_routes` | 公共路由 JSON | `load_constant_routes` |
| `role:{code}:menus` | 菜单 ID 列表 | `load_role_permissions` |
| `role:{code}:apis` | `[{method, path, status}]` | 同上 |
| `role:{code}:buttons` | 按钮编码列表 | 同上 |
| `role:{code}:data_scope` | `all` / `department` / `self` / `custom` | 同上 |
| `user:{uid}:roles` | 角色编码列表 | `load_user_roles` |
| `user:{uid}:role_home` | 首页 route_name | 同上 |
| `token_version:{uid}` | 整数版本号（INCR） | `invalidate_user_session` 等 |

读取（在 `DependAuth` / `DependPermission` 中使用）：

```python
from app.core.cache import (
    get_constant_routes,
    get_role_apis, get_role_menu_ids,
    get_user_role_codes, get_user_button_codes, get_user_role_home,
)
```

启动时 `refresh_all_cache(redis)` 一次性把所有数据加载进去。CUD 时**增量**刷新——例如修改某个角色后调 `await load_role_permissions(redis, role_code="R_HR_ADMIN")`，否则用户继续看缓存的旧权限。

### Redis 故障降级

`DependAuth` 在读 `get_user_role_codes / get_user_button_codes` 抛异常时，直接走数据库 fallback 加载（`user.fetch_related("by_user_roles")`）并打 WARNING：

```
Redis unavailable, loading permissions from database for user 123
```

`DependPermission` 与 `data_scope` 同样有 fallback。生产 Redis 故障时鉴权依然工作，只是延迟变高。

## 业务模块自有缓存

模块内的"统计 / 选项 / 聚合"类小热点直接读写 Redis。下例为通用模式（非仓库现存代码）：

```python
# app/business/<module>/services.py
import json

STATS_KEY = "<module>_<resource>:all"
STATS_TTL = 5 * 60  # 5 分钟

async def get_stats(redis):
    cached = await redis.get(STATS_KEY)
    if cached:
        return json.loads(cached)

    rows = await Model.annotate(...).group_by("xxx_id").values(...)
    await redis.set(STATS_KEY, json.dumps(rows, ensure_ascii=False), ex=STATS_TTL)
    return rows
```

业务变更时**主动失效**：

```python
# app/business/<module>/cache_utils.py（如需要）
async def invalidate_stats(redis):
    await redis.delete(STATS_KEY)
```

仓库内现存同模式参考 —— 字典选项缓存（[`app/system/api/dictionary.py`](../../../app/system/api/dictionary.py)）：

```python
@router.get("/dictionaries/{dict_type}/options")
async def get_dict_options(dict_type: str, request: Request):
    cache_key = f"dict_options:{dict_type}"
    cached = await request.app.state.redis.get(cache_key)
    if cached:
        return Success(data=json.loads(cached))
    ...
```

## fastapi-cache2

应用初始化时已经做了：

```python
FastAPICache.init(RedisBackend(_app.state.redis), prefix="fastapi-cache")
```

需要把整条接口缓存起来时用 `@cache(...)` 装饰器：

```python
from fastapi_cache.decorator import cache

@router.get("/heavy-report")
@cache(expire=60, namespace="reports")
async def _heavy_report(): ...
```

::: warning 不推荐对带分页/多参数的接口加全局 cache
key 由参数序列化生成，分页 + 过滤组合多时容易把 Redis 撑爆。能"按业务键"精控的小热点请走上一节的"主动管理"模式。
:::

## 缓存键命名约定

- 系统级权限：`role:{code}:*` / `user:{uid}:*`（不带模块前缀）
- 业务模块自有：`<module>_<resource>:<scope>`（带模块名前缀，避免冲突）
  - 例：`dict_options:tag_category`、`crm_lead_cnt:dept_42`
- 锁 / 协调键：`app:<purpose>`（例：`app:init_lock`、`app:init_done`）

## 启动时多 worker 锁

[`app/__init__.py`](../../../app/__init__.py) 的 `_run_init_data` 用两个 key：

| Key | 用途 | TTL |
|---|---|---|
| `app:init_lock` | leader 选举（`SET NX EX 120`） | 120s |
| `app:init_done` | leader 完成信号 | 120s |

每次进程启动前 leader 先 `DEL` 两个 key，因此每次重启都会真的跑一次 init。`reconcile_menu_subtree` 能正确生效就靠这一点。

## 调试技巧

```bash
# 查看角色权限缓存
redis-cli get "role:R_HR_ADMIN:apis" | jq

# 强制失效某用户的会话（让所有旧 token 立即作废）
redis-cli incr "token_version:123"

# 清空所有字典缓存（dictionary.py invalidate_dict_cache 也做这个）
redis-cli --scan --pattern "dict_options:*" | xargs redis-cli del

# 看启动锁
redis-cli get "app:init_done"
```

## 相关

- [RBAC](../develop/rbac.md) — 权限缓存怎么被 RBAC 用
- [认证](../develop/auth.md) — token_version 用法
- [启动初始化与对账](../develop/init-data.md) — `refresh_all_cache` 何时跑
