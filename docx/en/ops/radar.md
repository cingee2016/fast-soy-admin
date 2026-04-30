# Monitoring (Radar / Guard)

Two production-ready monitoring / protection systems:

- **Radar (in-house)** — request / SQL / exception / system-metric tracing with a Web Dashboard, implemented in this project with reference to fastapi-radar; source at `app/system/radar/`.
- **[fastapi-guard](https://fastapi-guard.com/)** — third-party rate limit + auto-ban (anti-scraping / brute force)

Configured in `app/core/config.py` and `app/core/init_app.py`.

## Radar (in-house)

Captures per request:

- path, method, status, duration
- every SQL the request executed (params + duration)
- exceptions raised
- developer-instrumented logs (`radar_log(...)`)

Data lands in Radar's lightweight DB (separate from the main DB), browsable from the menu "System / Performance":

| Path | Content |
|---|---|
| `/manage/radar/overview` | summary dashboard |
| `/manage/radar/requests` | request list (with full per-request timeline) |
| `/manage/radar/queries` | SQL query list (sorted by duration) |
| `/manage/radar/exceptions` | exception list |
| `/manage/radar/monitor` | system metrics (CPU / memory / DB connections) |

### Toggle

```bash
# .env
RADAR_ENABLED=true       # default true
```

When false, `setup_radar` / `startup_radar` skip; the menu still exists but endpoints return empty data.

> This project's Radar module is implemented with reference to fastapi-radar.

### radar_log — instrumentation

```python
from app.utils import radar_log

radar_log("login success", data={"userName": "admin", "userId": 1})
radar_log("permission denied", level="ERROR", data={"method": "POST", "path": "/x"})
radar_log("radar only, not file log", log_to_file=False)
```

Args:

| Arg | Default | Meaning |
|---|---|---|
| `message` | — | log body |
| `level` | `"INFO"` | `DEBUG / INFO / WARNING / ERROR / CRITICAL` |
| `data` | `None` | dict, JSON-serialized automatically |
| `log_to_file` | `True` | also log to Loguru file |

Effect:

- Loguru file log: `<time> | INFO | login success | {"userName": "admin", "userId": 1}`
- Radar Dashboard: appears in the request's "user logs" timeline with caller `module.func:line`

### Recommended use

| Scenario | Use |
|---|---|
| Critical business node (login / state change / payment) | `radar_log` + `data` |
| Permission denial / exception branch | `radar_log(level="ERROR", data=...)` |
| High-volume debug | `log.debug(...)`, not radar |
| Auto-captured request / SQL | radar already does it; don't duplicate |

## [fastapi-guard](https://fastapi-guard.com/)

Third-party per-request rate limit + auto-ban.

```bash
# .env
GUARD_ENABLED=true              # default true
GUARD_RATE_LIMIT=100            # requests per window
GUARD_RATE_LIMIT_WINDOW=60      # window size (seconds)
GUARD_AUTO_BAN_THRESHOLD=10     # violations before auto-ban
GUARD_AUTO_BAN_DURATION=21600   # ban duration (seconds, 6 hours)
```

Returns:

| Code | Meaning |
|---|---|
| `2500 RATE_LIMITED` | too many requests |
| `2501 IP_BANNED` | IP auto-banned |
| `2502 ACCESS_DENIED` | blocked by security policy |

### Behind a reverse proxy

Enable `PROXY_HEADERS_ENABLED=true` so granian reconciles `X-Forwarded-For` / `X-Forwarded-Proto` to the real client IP — guard relies on this. **Production behind Nginx must enable**, otherwise every request looks like the nginx container's IP and triggers blanket bans.

```bash
PROXY_HEADERS_ENABLED=true
TRUSTED_HOSTS=["127.0.0.1", "10.0.0.0/8"]   # trusted upstreams
```

### Banned — what to do

```bash
# Nuke guard's Redis counters / ban list
redis-cli --scan --pattern "fastapi_guard:*" | xargs redis-cli del
```

Or temporarily set `GUARD_ENABLED=false` and restart.

## Logging (Loguru)

- Configured in `app/core/log.py`
- Output dir: `logs/` (set by `APP_SETTINGS.LOGS_ROOT`)
- Retention: `LOG_INFO_RETENTION="30 days"` (supports `seconds/minutes/hours/days/weeks/months/years`)

In business code:

```python
from app.utils import log

log.info("..."); log.warning("..."); log.error("..."); log.exception("...")
```

`radar_log` calls Loguru internally — **don't** double-log.

## guard_core noise suppression

[fastapi-guard](https://fastapi-guard.com/)'s internal `guard_core` library installs its own StreamHandler with verbose INFO output. `create_app` clears its handlers and bumps the level to WARNING so business logs aren't drowned.

## See also

- [Auth / radar_log usage](/en/develop/auth#audit--radar_log)
- [Configuration](/en/ops/config) — RADAR / GUARD / PROXY env vars
