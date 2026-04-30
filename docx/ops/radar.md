# 监控（Radar / Guard）

后端内置两套生产可用的监控/防护：

- **Radar（内置）** — 参考 fastapi-radar 实现的请求 / SQL 查询 / 异常 / 系统指标 全栈追踪（含一个 Web Dashboard），源码位于 [`app/system/radar/`](../../../app/system/radar/)
- **[fastapi-guard](https://fastapi-guard.com/)** — 第三方限流 + 自动封禁（防爬虫 / 暴力破解）

配置在 [`app/core/config.py`](../../../app/core/config.py) 与 [`app/core/init_app.py`](../../../app/core/init_app.py)。

## Radar（内置）

捕获每次请求的：

- 请求路径、方法、状态码、耗时
- 该请求执行的所有 SQL（含参数与耗时）
- 该请求触发的异常
- 业务侧主动埋的日志（`radar_log(...)`）

数据写入 Radar 自带的轻量数据库（与主库分离），通过菜单"系统管理 / 性能监控"下五个页面查看：

| 路径 | 内容 |
|---|---|
| `/manage/radar/overview` | 总览仪表板 |
| `/manage/radar/requests` | 请求列表（含每条的完整时间线） |
| `/manage/radar/queries` | SQL 查询列表（按耗时排序） |
| `/manage/radar/exceptions` | 异常列表 |
| `/manage/radar/monitor` | 系统指标（CPU / 内存 / DB 连接数） |

### 启用 / 关闭

```bash
# .env
RADAR_ENABLED=true       # 默认 true
```

关闭后 `setup_radar` / `startup_radar` 都会跳过，前端菜单仍在但接口返回空数据。

> 本项目参考 fastapi-radar 实现。

### radar_log — 业务埋点

```python
from app.utils import radar_log

radar_log("用户登录成功", data={"userName": "admin", "userId": 1})
radar_log("权限拒绝", level="ERROR", data={"method": "POST", "path": "/x"})
radar_log("仅 radar，不落文件日志", log_to_file=False)
```

参数：

| 参数 | 默认 | 说明 |
|---|---|---|
| `message` | — | 日志正文 |
| `level` | `"INFO"` | `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL` |
| `data` | `None` | dict，自动 json 序列化 |
| `log_to_file` | `True` | 同时输出到 loguru 文件日志 |

效果：

- Loguru 文件日志：`<time> | INFO | 用户登录成功 | {"userName": "admin", "userId": 1}`
- Radar Dashboard：在该请求的"用户日志"时间线里附加一条，含调用方 `module.func:line`

### 推荐用法

| 场景 | 推荐 |
|---|---|
| 关键业务节点（登录、状态变更、支付） | `radar_log` + `data` |
| 权限拒绝 / 异常分支 | `radar_log(level="ERROR", data=...)` |
| 高频度调试日志 | 用 `log.debug(...)` 不上 radar |
| 请求 / SQL 自动捕获，不需要手写 | radar 已经做了，别重复 |

## [fastapi-guard](https://fastapi-guard.com/)

第三方请求级别的限流 + 自动封禁。

```bash
# .env
GUARD_ENABLED=true              # 默认 true
GUARD_RATE_LIMIT=100            # 每窗口内允许的请求数
GUARD_RATE_LIMIT_WINDOW=60      # 窗口大小（秒）
GUARD_AUTO_BAN_THRESHOLD=10     # 触发封禁的违规次数
GUARD_AUTO_BAN_DURATION=21600   # 封禁时长（秒，6 小时）
```

触发后返回：

| 码 | 说明 |
|---|---|
| `2500 RATE_LIMITED` | 请求过于频繁 |
| `2501 IP_BANNED` | IP 已被自动封禁 |
| `2502 ACCESS_DENIED` | 被安全策略拦截 |

### 反代场景

启用 `PROXY_HEADERS_ENABLED=true` 后 `granian` 会从 `X-Forwarded-For` / `X-Forwarded-Proto` 还原真实客户端 IP，guard 才能正确识别。**生产环境部署在 Nginx 之后务必启用**，否则所有请求都会被识别为 nginx 容器的 IP，触发误封。

```bash
PROXY_HEADERS_ENABLED=true
TRUSTED_HOSTS=["127.0.0.1", "10.0.0.0/8"]   # 信任的上游
```

### 排查"被封了怎么办"

```bash
# 直接清掉 guard 的 Redis 计数 / 封禁名单
redis-cli --scan --pattern "fastapi_guard:*" | xargs redis-cli del
```

或者 .env 里临时把 `GUARD_ENABLED=false` 重启。

## 日志（Loguru）

- 配置在 [`app/core/log.py`](../../../app/core/log.py)
- 日志输出位置：`logs/`（由 `APP_SETTINGS.LOGS_ROOT` 指定）
- 普通日志保留时间：`LOG_INFO_RETENTION="30 days"`（支持 `seconds/minutes/hours/days/weeks/months/years`）

业务里直接：

```python
from app.utils import log

log.info("..."); log.warning("..."); log.error("..."); log.exception("...")
```

`radar_log` 内部会同时调用 loguru，所以**不需要重复**写两次。

## guard_core 日志噪音抑制

[fastapi-guard](https://fastapi-guard.com/) 的内部库 `guard_core` 会自己加 StreamHandler 并输出冗长 INFO，[`create_app`](../../../app/__init__.py) 启动时会清掉它的 handler 并把级别提到 WARNING，不影响业务日志。

## 相关

- [认证 / radar_log 用法](../develop/auth.md#操作审计--radar_log)
- [配置](./config.md) — RADAR / GUARD / PROXY 相关 env 全集
