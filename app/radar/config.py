from pathlib import Path

from pydantic_settings import BaseSettings

from app.settings import APP_SETTINGS


class RadarSettings(BaseSettings):
    RADAR_ENABLED: bool = True
    RADAR_DB_PATH: Path = APP_SETTINGS.BASE_DIR / "radar.sqlite3"
    RADAR_RETENTION_HOURS: int = 24
    RADAR_MAX_BODY_SIZE: int = 65536
    RADAR_EXCLUDE_PATHS: list[str] = ["/__radar", "/static", "/docs", "/openapi.json", "/redoc", "/doc", "/api/v1/monitor/"]
    RADAR_SLOW_QUERY_THRESHOLD_MS: float = 100.0
    RADAR_CAPTURE_RESPONSE_BODY: bool = True

    model_config = {"env_prefix": "RADAR_", "env_file": ".env", "extra": "ignore"}


RADAR_SETTINGS = RadarSettings()
