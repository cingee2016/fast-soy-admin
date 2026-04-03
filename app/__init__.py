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
    modify_db,
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


@asynccontextmanager
async def lifespan(_app: FastAPI):
    start_time = datetime.now()
    _app.state.redis = await init_redis()
    FastAPICache.init(RedisBackend(_app.state.redis), prefix="fastapi-cache")
    try:
        await modify_db()
        await init_menus()
        await refresh_api_list()
        await init_users()
        # 业务模块初始化数据（菜单、按钮、角色）— 在 API 注册之后、缓存刷新之前
        from app.core.autodiscover import discover_business_init_data

        for init_fn in discover_business_init_data():
            await init_fn()
        # 启动时刷新所有缓存：清除 fastapi-cache2 + 常量路由 + 角色权限 + token 版本号
        await refresh_all_cache(_app.state.redis)
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
