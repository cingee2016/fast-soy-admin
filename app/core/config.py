from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings


def tortoise_orm_factory() -> dict[str, Any]:
    from app.core.autodiscover import discover_business_models

    models = ["app.system.models", "app.system.radar.models"] + discover_business_models()
    return {
        "connections": {"conn_system": {"engine": "tortoise.backends.sqlite", "credentials": {"file_path": "app_system.sqlite3"}}},
        "apps": {"app_system": {"models": models, "default_connection": "conn_system", "migrations": "migrations.app_system"}},
        "use_tz": False,
        "timezone": "Asia/Shanghai",
    }


class Settings(BaseSettings):
    VERSION: str = "0.1.0"
    APP_TITLE: str = "FastSoyAdmin"
    APP_DESCRIPTION: str = "Description"

    CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["*"])
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = Field(default_factory=lambda: ["*"])
    CORS_ALLOW_HEADERS: list[str] = Field(default_factory=lambda: ["*"])

    DEBUG: bool = False
    RADAR_ENABLED: bool = True

    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
    BASE_DIR: Path = PROJECT_ROOT.parent
    LOGS_ROOT: Path = BASE_DIR / "logs/"
    STATIC_ROOT: Path = BASE_DIR / "static/"
    SECRET_KEY: str = "015a42020f023ac2c3eda3d45fe5ca3fef8921ce63589f6d4fcdef9814cd7fa7"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12  # 12 hours
    JWT_REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    TORTOISE_ORM: dict[str, Any] = Field(default_factory=tortoise_orm_factory)

    DATETIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"

    REDIS_URL: str = "redis://redis:6379/0"  # "redis://:password@233.233.233.233:33333/0"

    # logs - 普通日志保留时间, 支持: seconds/minutes/hours/days/weeks/months/years (如 "30 days", "1 months", "2 weeks")
    LOG_INFO_RETENTION: str = "30 days"

    # fastapi-guard
    GUARD_ENABLED: bool = True
    GUARD_RATE_LIMIT: int = 100
    GUARD_RATE_LIMIT_WINDOW: int = 60
    GUARD_AUTO_BAN_THRESHOLD: int = 10
    GUARD_AUTO_BAN_DURATION: int = 21600

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


APP_SETTINGS = Settings()
TORTOISE_ORM = APP_SETTINGS.TORTOISE_ORM

# Ensure required directories exist
for _dir in [APP_SETTINGS.LOGS_ROOT, APP_SETTINGS.STATIC_ROOT, APP_SETTINGS.BASE_DIR / "migrations"]:
    _dir.mkdir(parents=True, exist_ok=True)
