"""System monitor API endpoints."""

from __future__ import annotations

import asyncio
from functools import partial

from fastapi import APIRouter, Query

from app.services.monitor import collector

router = APIRouter(prefix="/monitor")


def _run_sync(fn, *args, **kwargs):  # type: ignore[no-untyped-def]
    return fn(*args, **kwargs)


@router.get("/overview", summary="系统监控概览")
async def get_overview():
    data = await asyncio.to_thread(partial(_run_sync, collector.get_overview))
    return {"code": "0000", "msg": "OK", "data": data}


@router.get("/realtime", summary="实时监控数据")
async def get_realtime():
    data = await asyncio.to_thread(partial(_run_sync, collector.get_realtime))
    return {"code": "0000", "msg": "OK", "data": data}


@router.get("/basic-info", summary="基本信息")
async def get_basic_info():
    data = await asyncio.to_thread(partial(_run_sync, collector.get_basic_info))
    return {"code": "0000", "msg": "OK", "data": data}


@router.get("/processes", summary="Top进程")
async def get_processes(limit: int = Query(default=10, ge=1, le=50)):
    data = await asyncio.to_thread(partial(_run_sync, collector.get_top_processes, limit))
    return {"code": "0000", "msg": "OK", "data": data}
