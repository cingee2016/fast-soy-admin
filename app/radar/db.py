from __future__ import annotations

from datetime import datetime, timedelta

from loguru import logger
from tortoise.expressions import Q

from app.radar.ctx import RadarRequestContext
from app.radar.models import RadarQuery, RadarRequest, RadarUserLog


async def flush_request_data(ctx: RadarRequestContext) -> None:
    import time

    from app.radar.query_capture import CTX_RADAR_WRITING

    token = CTX_RADAR_WRITING.set(True)
    try:
        duration_ms = round((time.monotonic() - ctx.start_mono) * 1000, 3)

        req_obj = await RadarRequest.create(
            x_request_id=ctx.x_request_id,
            method=ctx.method,
            path=ctx.path,
            query_params=ctx.query_params,
            request_headers=ctx.request_headers,
            request_body=ctx.request_body,
            response_status=ctx.response_status,
            response_headers=ctx.response_headers,
            response_body=ctx.response_body,
            duration_ms=duration_ms,
            error_type=ctx.exception_info.get("type") if ctx.exception_info else None,
            error_message=ctx.exception_info.get("message") if ctx.exception_info else None,
            error_traceback=ctx.exception_info.get("traceback") if ctx.exception_info else None,
        )

        if ctx.queries:
            await RadarQuery.bulk_create([
                RadarQuery(
                    request=req_obj,
                    sql_text=q["sql"],
                    params=q.get("params"),
                    operation=q.get("operation"),
                    duration_ms=q["duration_ms"],
                    connection_name=q.get("connection_name"),
                    start_offset_ms=q.get("start_offset_ms"),
                )
                for q in ctx.queries
            ])

        if ctx.user_logs:
            await RadarUserLog.bulk_create([
                RadarUserLog(
                    request=req_obj,
                    level=ul["level"],
                    message=ul["message"],
                    data=ul.get("data"),
                    source=ul.get("source"),
                    offset_ms=ul.get("offset_ms"),
                )
                for ul in ctx.user_logs
            ])
    except Exception:
        logger.exception("Failed to flush radar data")
    finally:
        CTX_RADAR_WRITING.reset(token)


async def purge_old_data(retention_hours: int = 24) -> int:
    from app.radar.query_capture import CTX_RADAR_WRITING

    token = CTX_RADAR_WRITING.set(True)
    try:
        cutoff = datetime.now() - timedelta(hours=retention_hours)
        deleted = await RadarRequest.filter(created_at__lt=cutoff).delete()
        return deleted
    finally:
        CTX_RADAR_WRITING.reset(token)


async def query_requests(
    page: int = 1,
    page_size: int = 20,
    path_filter: str | None = None,
    status_filter: int | None = None,
    min_duration: float | None = None,
    has_error: bool | None = None,
) -> tuple[int, list[dict]]:
    q = Q()
    if path_filter:
        q &= Q(path__contains=path_filter)
    if status_filter is not None:
        q &= Q(response_status=status_filter)
    if min_duration is not None:
        q &= Q(duration_ms__gte=min_duration)
    if has_error is True:
        q &= Q(error_type__not_isnull=True)
    elif has_error is False:
        q &= Q(error_type__isnull=True)

    total = await RadarRequest.filter(q).count()
    offset = (page - 1) * page_size
    objs = await RadarRequest.filter(q).order_by("-id").offset(offset).limit(page_size)
    records = [await obj.to_dict() for obj in objs]
    return total, records


async def query_request_detail(x_request_id: str) -> dict | None:
    req = await RadarRequest.filter(x_request_id=x_request_id).first()
    if not req:
        return None

    result = await req.to_dict()

    query_objs = await RadarQuery.filter(request=req).order_by("start_offset_ms")
    result["queries"] = [await q.to_dict() for q in query_objs]

    log_objs = await RadarUserLog.filter(request=req).order_by("offset_ms")
    result["user_logs"] = [await ul.to_dict() for ul in log_objs]

    return result


async def query_request_timeline(x_request_id: str) -> list[dict]:
    req = await RadarRequest.filter(x_request_id=x_request_id).first()
    if not req:
        return []

    timeline: list[dict] = []

    query_objs = await RadarQuery.filter(request=req).order_by("start_offset_ms")
    for q in query_objs:
        timeline.append({
            "type": "query",
            "name": f"{q.operation} query",
            "sql": q.sql_text,
            "start_offset_ms": q.start_offset_ms,
            "duration_ms": q.duration_ms,
        })

    log_objs = await RadarUserLog.filter(request=req).order_by("offset_ms")
    for ul in log_objs:
        timeline.append({
            "type": "user_log",
            "name": f"[{ul.level}] {ul.message}",
            "start_offset_ms": ul.offset_ms,
            "duration_ms": 0,
        })

    if req.error_type:
        timeline.append({
            "type": "exception",
            "name": f"Exception: {req.error_type}",
            "start_offset_ms": req.duration_ms or 0,
            "duration_ms": 0,
        })

    timeline.sort(key=lambda x: x.get("start_offset_ms") or 0)
    return timeline


async def query_all_queries(
    page: int = 1,
    page_size: int = 20,
    slow_only: bool = False,
    threshold_ms: float = 100.0,
) -> tuple[int, list[dict]]:
    q = Q()
    if slow_only:
        q &= Q(duration_ms__gte=threshold_ms)

    total = await RadarQuery.filter(q).count()
    offset = (page - 1) * page_size
    objs = await RadarQuery.filter(q).order_by("-duration_ms").offset(offset).limit(page_size)
    records = [await obj.to_dict() for obj in objs]
    return total, records


async def query_exceptions(page: int = 1, page_size: int = 20) -> tuple[int, list[dict]]:
    q = Q(error_type__not_isnull=True)
    total = await RadarRequest.filter(q).count()
    offset = (page - 1) * page_size
    objs = await RadarRequest.filter(q).order_by("-id").offset(offset).limit(page_size)
    records = []
    for obj in objs:
        records.append(await obj.to_dict(include_fields=["x_request_id", "method", "path", "error_type", "error_message", "error_traceback", "duration_ms", "created_at"]))
    return total, records


async def query_user_logs(page: int = 1, page_size: int = 20, level: str | None = None) -> tuple[int, list[dict]]:
    q = Q()
    if level:
        q &= Q(level=level.upper())

    total = await RadarUserLog.filter(q).count()
    offset = (page - 1) * page_size
    objs = await RadarUserLog.filter(q).order_by("-id").offset(offset).limit(page_size)
    records = [await obj.to_dict() for obj in objs]
    return total, records


async def query_stats() -> dict:
    from app.radar.config import RADAR_SETTINGS

    req_count = await RadarRequest.all().count()
    from tortoise.functions import Avg

    avg_row = await RadarRequest.all().annotate(avg_dur=Avg("duration_ms")).first().values("avg_dur")
    avg_duration: float = avg_row["avg_dur"] if avg_row and avg_row.get("avg_dur") is not None else 0
    error_count = await RadarRequest.filter(error_type__not_isnull=True).count()
    query_count = await RadarQuery.all().count()
    slow_query_count = await RadarQuery.filter(duration_ms__gte=RADAR_SETTINGS.RADAR_SLOW_QUERY_THRESHOLD_MS).count()
    user_log_count = await RadarUserLog.all().count()

    return {
        "request_count": req_count,
        "avg_duration_ms": round(avg_duration, 3) if avg_duration else 0,
        "error_count": error_count,
        "error_rate": round(error_count / req_count * 100, 2) if req_count else 0,
        "query_count": query_count,
        "slow_query_count": slow_query_count,
        "user_log_count": user_log_count,
    }
