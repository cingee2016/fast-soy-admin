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


async def modify_db():
    from tortoise.migrations.api.migrate import migrate

    try:
        await migrate(config=APP_SETTINGS.TORTOISE_ORM, app_labels=["app_system"])
    except Exception:
        ...

    # migrate() → Tortoise.init() → close_connections() clears _global_context.
    # Restore it so request handlers (running in separate tasks) can find the context.
    from tortoise.context import _global_context, get_current_context, set_global_context

    if _global_context is None:
        ctx = get_current_context()
        if ctx is not None:
            set_global_context(ctx)
