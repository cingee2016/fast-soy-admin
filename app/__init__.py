from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from starlette.staticfiles import StaticFiles

from app.api.health import router as health_router
from app.api.v1.utils import refresh_api_list
from app.core.exceptions import SettingNotFound
from app.core.init_app import (
    init_menus,
    init_users,
    make_middlewares,
    modify_db,
    register_db,
    register_exceptions,
    register_routers,
)
from app.core.redis import close_redis, init_redis
from app.log import log

try:
    from app.settings import APP_SETTINGS
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
    _app.include_router(health_router)
    from app.monitor import monitor_router

    _app.include_router(monitor_router)
    if APP_SETTINGS.RADAR_ENABLED:
        from app.radar import setup_radar

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
        await _ensure_monitor_menu()
        await refresh_api_list()
        await init_users()
        await _load_token_versions(_app.state.redis)
        if APP_SETTINGS.RADAR_ENABLED:
            from app.radar import startup_radar

            await startup_radar()
        yield

    finally:
        if APP_SETTINGS.RADAR_ENABLED:
            from app.radar import shutdown_radar

            await shutdown_radar()
        end_time = datetime.now()
        runtime = (end_time - start_time).total_seconds() / 60
        log.info(f"App {_app.title} runtime: {runtime} min")  # noqa
        await close_redis(_app.state.redis)


async def _load_token_versions(redis):
    """启动时将数据库中所有用户的 token_version 加载到 Redis"""
    from app.models.system.admin import User

    users = await User.all().values_list("id", "token_version")
    pipe = redis.pipeline()
    for user_id, token_version in users:
        pipe.set(f"token_version:{user_id}", token_version)
    await pipe.execute()
    log.info(f"Loaded token_version for {len(users)} users into Redis")


async def _ensure_monitor_menu():
    """Insert manage_radar_monitor menu if missing (for existing databases)."""
    from app.models.system.admin import Menu
    from app.models.system.utils import IconType, MenuType, StatusType

    if await Menu.filter(route_name="manage_radar_monitor").exists():
        return
    radar_parent = await Menu.filter(route_name="manage_radar").first()
    if not radar_parent:
        return
    await Menu.create(
        status_type=StatusType.enable,
        parent_id=radar_parent.id,
        menu_type=MenuType.menu,
        menu_name="系统监控",
        route_name="manage_radar_monitor",
        route_path="/manage/radar/monitor",
        component="view.manage_radar_monitor",
        order=5,
        i18n_key="route.manage_radar_monitor",
        icon="mdi:monitor-dashboard",
        icon_type=IconType.iconify,
    )
    # Also update overview menu name
    await Menu.filter(route_name="manage_radar_overview").update(menu_name="仪表板")


app = create_app()

app.mount("/static", StaticFiles(directory=APP_SETTINGS.STATIC_ROOT), name="static")
