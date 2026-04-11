from __future__ import annotations

from fastapi import FastAPI

from app.system.radar.api import router as radar_router
from app.system.radar.config import RADAR_SETTINGS
from app.system.radar.query_capture import install_query_capture, uninstall_query_capture


def setup_radar(app: FastAPI) -> None:
    if not RADAR_SETTINGS.RADAR_ENABLED:
        return

    app.include_router(radar_router)


async def startup_radar() -> None:
    if not RADAR_SETTINGS.RADAR_ENABLED:
        return

    install_query_capture()


async def shutdown_radar() -> None:
    if not RADAR_SETTINGS.RADAR_ENABLED:
        return

    uninstall_query_capture()
