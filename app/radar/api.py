from __future__ import annotations

import json

from fastapi import APIRouter, Query

from app.radar import db
from app.radar.config import RADAR_SETTINGS

router = APIRouter(prefix="/__radar/api", tags=["Radar"])


@router.get("/requests", summary="请求列表")
async def list_requests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    path_filter: str | None = None,
    status_filter: int | None = None,
    min_duration: float | None = None,
    has_error: bool | None = None,
):
    total, rows = await db.query_requests(
        page=page,
        page_size=page_size,
        path_filter=path_filter,
        status_filter=status_filter,
        min_duration=min_duration,
        has_error=has_error,
    )
    return {"code": "0000", "msg": "OK", "data": {"total": total, "current": page, "size": page_size, "records": rows}}


@router.get("/requests/{x_request_id}", summary="请求详情")
async def get_request_detail(x_request_id: str):
    detail = await db.query_request_detail(x_request_id)
    if not detail:
        return {"code": "4004", "msg": "Request not found", "data": None}

    # Parse JSON strings back to dicts for display (keys are camelCase from to_dict)
    for field in ("requestHeaders", "responseHeaders"):
        if detail.get(field) and isinstance(detail[field], str):
            try:
                detail[field] = json.loads(detail[field])
            except (json.JSONDecodeError, TypeError):
                pass

    return {"code": "0000", "msg": "OK", "data": detail}


@router.get("/requests/{x_request_id}/timeline", summary="请求时间线")
async def get_request_timeline(x_request_id: str):
    timeline = await db.query_request_timeline(x_request_id)
    return {"code": "0000", "msg": "OK", "data": timeline}


@router.get("/queries", summary="SQL查询列表")
async def list_queries(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    slow_only: bool = False,
    threshold_ms: float | None = None,
):
    total, rows = await db.query_all_queries(
        page=page,
        page_size=page_size,
        slow_only=slow_only,
        threshold_ms=threshold_ms or RADAR_SETTINGS.RADAR_SLOW_QUERY_THRESHOLD_MS,
    )
    return {"code": "0000", "msg": "OK", "data": {"total": total, "current": page, "size": page_size, "records": rows}}


@router.get("/queries/slow", summary="慢查询排行")
async def list_slow_queries(
    limit: int = Query(20, ge=1, le=100),
):
    _, rows = await db.query_all_queries(
        page=1,
        page_size=limit,
        slow_only=True,
        threshold_ms=RADAR_SETTINGS.RADAR_SLOW_QUERY_THRESHOLD_MS,
    )
    return {"code": "0000", "msg": "OK", "data": rows}


@router.get("/exceptions", summary="异常列表")
async def list_exceptions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    total, rows = await db.query_exceptions(page=page, page_size=page_size)
    return {"code": "0000", "msg": "OK", "data": {"total": total, "current": page, "size": page_size, "records": rows}}


@router.get("/user-logs", summary="开发者手动日志")
async def list_user_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    level: str | None = None,
):
    total, rows = await db.query_user_logs(page=page, page_size=page_size, level=level)
    return {"code": "0000", "msg": "OK", "data": {"total": total, "current": page, "size": page_size, "records": rows}}


@router.get("/stats", summary="统计概览")
async def get_stats():
    stats = await db.query_stats()
    return {"code": "0000", "msg": "OK", "data": stats}


@router.delete("/purge", summary="清理过期数据")
async def purge_data(retention_hours: int = Query(default=24, ge=1)):
    deleted = await db.purge_old_data(retention_hours=retention_hours)
    return {"code": "0000", "msg": "OK", "data": {"deleted_count": deleted}}
