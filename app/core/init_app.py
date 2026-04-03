import pretty_errors
from fastapi import FastAPI
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from tortoise.contrib.fastapi import register_tortoise

from app.core.config import APP_SETTINGS
from app.core.exceptions import (
    DoesNotExist,
    DoesNotExistHandle,
    HTTPException,
    HttpExcHandle,
    IntegrityError,
    IntegrityHandle,
    RequestValidationError,
    RequestValidationHandle,
    ResponseValidationError,
    ResponseValidationHandle,
)
from app.core.middlewares import BackGroundTaskMiddleware, PrettyErrorsMiddleware, RequestIDMiddleware


async def _guard_response_modifier(response):
    """Rewrite guard error responses to the project's unified JSON format."""
    import orjson
    from starlette.responses import Response

    from app.core.code import Code

    status = response.status_code
    if status < 400:
        return response
    if status == 404:
        return response  # let normal 404 pass through, don't mask as security block
    if status == 429:
        code, msg = Code.RATE_LIMITED, "请求过于频繁，请稍后再试"
    elif status == 403 and b"banned" in (response.body or b"").lower():
        code, msg = Code.IP_BANNED, "IP已被封禁，请稍后再试"
    elif status == 403:
        code, msg = Code.ACCESS_DENIED, "访问被拒绝"
    else:
        code, msg = Code.ACCESS_DENIED, "请求被安全策略拦截"
    body = orjson.dumps({"code": code, "msg": msg, "data": None})
    response._response = Response(content=body, status_code=200, media_type="application/json")
    return response


def _make_guard_config():
    """Create fastapi-guard SecurityConfig from app settings."""
    from guard import SecurityConfig

    return SecurityConfig(
        rate_limit=APP_SETTINGS.GUARD_RATE_LIMIT,
        rate_limit_window=APP_SETTINGS.GUARD_RATE_LIMIT_WINDOW,
        auto_ban_threshold=APP_SETTINGS.GUARD_AUTO_BAN_THRESHOLD,
        auto_ban_duration=APP_SETTINGS.GUARD_AUTO_BAN_DURATION,
        enable_redis=True,
        redis_url=APP_SETTINGS.REDIS_URL,
        enable_cors=False,  # CORS already handled by CORSMiddleware
        enforce_https=False,
        security_headers=None,  # Let nginx handle security headers
        custom_log_file=str(APP_SETTINGS.LOGS_ROOT / "guard.log"),
        custom_response_modifier=_guard_response_modifier,
        exclude_paths=["/docs", "/redoc", "/openapi.json", "/favicon.ico", "/static"],
        endpoint_rate_limits={
            "/api/v1/auth/login": (5, 60),  # 5 requests per 60 seconds
            "/api/v1/auth/refresh-token": (10, 60),  # 10 requests per 60 seconds
        },
    )


def make_middlewares():
    middleware = [
        Middleware(
            PrettyErrorsMiddleware,
            line_number_first=True,
            lines_before=5,
            lines_after=2,
            line_color=pretty_errors.RED + "> " + pretty_errors.default_config.line_color,
            code_color="  " + pretty_errors.default_config.line_color,
            truncate_code=True,
            display_locals=True,
            filename_display=pretty_errors.FILENAME_EXTENDED,
        ),
        Middleware(
            CORSMiddleware,
            allow_origins=APP_SETTINGS.CORS_ORIGINS,
            allow_credentials=APP_SETTINGS.CORS_ALLOW_CREDENTIALS,
            allow_methods=APP_SETTINGS.CORS_ALLOW_METHODS,
            allow_headers=APP_SETTINGS.CORS_ALLOW_HEADERS,
        ),
        Middleware(BackGroundTaskMiddleware),
        Middleware(RequestIDMiddleware),
    ]
    if APP_SETTINGS.GUARD_ENABLED:
        from guard.middleware import SecurityMiddleware

        middleware.append(Middleware(SecurityMiddleware, config=_make_guard_config()))

    if APP_SETTINGS.RADAR_ENABLED:
        from app.system.radar.middleware import RadarMiddleware

        middleware.append(Middleware(RadarMiddleware))
    return middleware


def register_db(app: FastAPI):
    register_tortoise(
        app,
        config=APP_SETTINGS.TORTOISE_ORM,
        generate_schemas=False,
    )


def register_exceptions(app: FastAPI):
    app.add_exception_handler(DoesNotExist, DoesNotExistHandle)
    app.add_exception_handler(HTTPException, HttpExcHandle)  # type: ignore
    app.add_exception_handler(IntegrityError, IntegrityHandle)
    app.add_exception_handler(RequestValidationError, RequestValidationHandle)  # type: ignore
    app.add_exception_handler(ResponseValidationError, ResponseValidationHandle)  # type: ignore


def register_routers(app: FastAPI, prefix: str = "/api"):
    from app.system.api import system_router
    from app.system.api.health import router as health_router

    app.include_router(system_router, prefix=f"{prefix}/v1")
    app.include_router(health_router)


def _ensure_migrations_dir():
    """确保 migrations 包目录存在，等价于 `tortoise init`。"""
    from tortoise.cli.cli import _ensure_migrations_package

    for app_label, app_config in APP_SETTINGS.TORTOISE_ORM.get("apps", {}).items():
        try:
            _ensure_migrations_package(app_label, app_config)
        except Exception:
            pass


def _has_migration_files(app_label: str) -> bool:
    """检查指定 app 是否已有迁移文件。"""
    from tortoise.migrations.writer import migrations_module_path

    migrations_module = APP_SETTINGS.TORTOISE_ORM.get("apps", {}).get(app_label, {}).get("migrations")
    if not migrations_module:
        return False
    try:
        path = migrations_module_path(migrations_module)
    except Exception:
        return False
    return any(f.suffix == ".py" and f.stem not in ("__init__",) for f in path.iterdir())


async def _auto_makemigrations(app_label: str):
    """为系统 app 自动生成迁移文件（等价于 tortoise makemigrations）。"""
    from tortoise import Tortoise
    from tortoise.migrations.autodetector import MigrationAutodetector

    from app.core.log import log

    apps_config = {app_label: APP_SETTINGS.TORTOISE_ORM["apps"][app_label]}
    autodetector = MigrationAutodetector(Tortoise.apps, apps_config)
    writers = await autodetector.changes()
    for writer in writers:
        path = writer.write()
        log.info(f"Auto-generated migration: {writer.app_label}.{writer.name} -> {path}")


async def ensure_system_tables():
    """确保系统表存在（幂等）。

    完整流程（等价于 tortoise init + makemigrations + migrate）：
    0. 确保迁移目录存在
    1. 若无迁移文件，自动生成（仅系统 app）
    2. 执行迁移
    业务模块不自动迁移，需开发者手动执行 tortoise makemigrations && tortoise migrate。
    """
    from tortoise.migrations.api.migrate import migrate

    from app.core.log import log

    # 0) 确保迁移目录存在（等价于 tortoise init）
    _ensure_migrations_dir()

    # 1) 若系统 app 无迁移文件，自动生成（等价于 tortoise makemigrations）
    if not _has_migration_files("app_system"):
        log.info("No migration files found for app_system, auto-generating...")
        await _auto_makemigrations("app_system")

    # 2) 执行迁移（等价于 tortoise migrate）
    try:
        await migrate(config=APP_SETTINGS.TORTOISE_ORM, app_labels=["app_system"])
    except Exception as e:
        log.warning(f"tortoise migrate skipped: {e}")

    # migrate() → Tortoise.init() → close_connections() 会清除 _global_context，需要恢复
    from tortoise.context import _global_context, get_current_context, set_global_context

    if _global_context is None:
        ctx = get_current_context()
        if ctx is not None:
            set_global_context(ctx)
