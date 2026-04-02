from __future__ import annotations

from fastapi import FastAPI
from loguru import logger

from app.system.radar.config import RADAR_SETTINGS


def setup_radar(app: FastAPI) -> None:
    if not RADAR_SETTINGS.RADAR_ENABLED:
        return

    from app.system.radar.api import router as radar_router

    app.include_router(radar_router)
    logger.info("Radar: API routes registered at /__radar/api")


async def startup_radar() -> None:
    if not RADAR_SETTINGS.RADAR_ENABLED:
        return

    from app.system.radar.query_capture import install_query_capture

    install_query_capture()
    logger.info("Radar: query capture installed")


async def shutdown_radar() -> None:
    if not RADAR_SETTINGS.RADAR_ENABLED:
        return

    from app.system.radar.query_capture import uninstall_query_capture

    uninstall_query_capture()
    logger.info("Radar: query capture uninstalled")
