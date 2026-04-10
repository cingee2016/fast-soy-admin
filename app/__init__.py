import asyncio
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from starlette.staticfiles import StaticFiles

from app.core.cache import refresh_all_cache
from app.core.exceptions import SettingNotFound
from app.core.init_app import (
    make_middlewares,
    register_db,
    register_exceptions,
    register_routers,
)
from app.core.log import log
from app.core.redis import close_redis, init_redis
from app.system.api.utils import refresh_api_list
from app.system.init_data import init_menus, init_users

try:
    from app.core.config import APP_SETTINGS
except ImportError:
    raise SettingNotFound("Can not import settings")

# Redis key used to coordinate multi-worker startup init
_INIT_LOCK_KEY = "app:init_lock"
_INIT_DONE_KEY = "app:init_done"
_INIT_LOCK_TIMEOUT = 120  # seconds — max time one worker holds the lock
_INIT_WAIT_TIMEOUT = 150  # seconds — max time other workers wait


def create_app() -> FastAPI:
    if APP_SETTINGS.DEBUG:
        _app = FastAPI(
            title=APP_SETTINGS.APP_TITLE, description=APP_SETTINGS.APP_DESCRIPTION, version=APP_SETTINGS.VERSION, openapi_url="/openapi.json", middleware=make_middlewares(), lifespan=lifespan
        )
    else:
        _app = FastAPI(title=APP_SETTINGS.APP_TITLE, description=APP_SETTINGS.APP_DESCRIPTION, version=APP_SETTINGS.VERSION, openapi_url=None, middleware=make_middlewares(), lifespan=lifespan)
    register_db(_app)
    register_exceptions(_app)
    register_routers(_app, prefix="/api")

    # Auto-discover and register business routes
    from app.core.autodiscover import discover_business_routers

    business_router = discover_business_routers()
    if business_router.routes:
        _app.include_router(business_router, prefix="/api/v1/business")

    if APP_SETTINGS.RADAR_ENABLED:
        from app.system.radar import setup_radar

        setup_radar(_app)
    return _app


async def _run_init_data(_app: FastAPI) -> None:
    """初始化种子数据和缓存。多 worker 下仅由一个进程执行，其余等待完成信号。"""
    redis = _app.state.redis

    # 清除上次启动遗留的完成标记
    acquired = await redis.set(_INIT_LOCK_KEY, "1", nx=True, ex=_INIT_LOCK_TIMEOUT)

    if acquired:
        # 当前 worker 负责初始化
        try:
            await init_menus()
            await refresh_api_list()
            await init_users()

            from app.core.autodiscover import discover_business_init_data

            for init_fn in discover_business_init_data():
                await init_fn()

            await refresh_all_cache(redis)
            # 通知其他 worker 初始化完成
            await redis.set(_INIT_DONE_KEY, "1", ex=_INIT_LOCK_TIMEOUT)
            log.info("Init data completed (leader worker)")
        except Exception:
            await redis.delete(_INIT_LOCK_KEY)
            raise
    else:
        # 其他 worker 等待初始化完成
        log.info("Waiting for leader worker to finish init data...")
        elapsed = 0.0
        while elapsed < _INIT_WAIT_TIMEOUT:
            if await redis.exists(_INIT_DONE_KEY):
                log.info("Init data done (follower worker)")
                return
            await asyncio.sleep(0.5)
            elapsed += 0.5
        log.warning("Init wait timed out — proceeding anyway")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    start_time = datetime.now()
    _app.state.redis = await init_redis()
    FastAPICache.init(RedisBackend(_app.state.redis), prefix="fastapi-cache")
    try:
        # 清除上一次启动遗留的锁（新一轮部署）
        await _app.state.redis.delete(_INIT_LOCK_KEY, _INIT_DONE_KEY)
        await _run_init_data(_app)

        if APP_SETTINGS.RADAR_ENABLED:
            from app.system.radar import startup_radar

            await startup_radar()
        yield

    finally:
        if APP_SETTINGS.RADAR_ENABLED:
            from app.system.radar import shutdown_radar

            await shutdown_radar()
        end_time = datetime.now()
        runtime = (end_time - start_time).total_seconds() / 60
        log.info(f"App {_app.title} runtime: {runtime} min")  # noqa
        await close_redis(_app.state.redis)


app = create_app()

app.mount("/static", StaticFiles(directory=APP_SETTINGS.STATIC_ROOT), name="static")
