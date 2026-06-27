from __future__ import annotations

import inspect
from datetime import datetime, timedelta, timezone
from typing import Any

from tortoise.expressions import Q
from tortoise.transactions import in_transaction

from app.core.business import EventSpec, PeriodicTask
from app.core.crud import get_db_conn


def serialize_event_payload(event: EventSpec, payload: dict[str, Any]) -> dict[str, Any]:
    if event.payload is None:
        return payload
    validated = event.payload.model_validate(payload)
    return validated.model_dump(mode="json")


async def enqueue_outbox_event(event: EventSpec, payload: dict[str, Any]) -> int:
    from app.system.models import EventOutbox

    row = await EventOutbox.create(
        event_name=event.name,
        event_version=event.version,
        payload=serialize_event_payload(event, payload),
    )
    return row.id


async def dispatch_outbox_once(*, limit: int = 50, max_attempts: int = 5) -> int:
    """Dispatch pending outbox events once.

    This is intentionally small: it executes local event handlers and records
    retry state. External brokers can be wired later without changing the event
    contract.
    """

    from app.core.events import emit_local
    from app.system.models import EventOutbox

    now = datetime.now(tz=timezone.utc)
    search = Q(status="pending") | Q(status="failed", next_retry_at__lte=now)
    rows = await EventOutbox.filter(search).order_by("id").limit(limit)
    dispatched = 0

    for row in rows:
        async with in_transaction(get_db_conn(EventOutbox)):
            locked = await EventOutbox.filter(id=row.id, status__in=["pending", "failed"]).update(status="processing", locked_at=now)
            if not locked:
                continue
        try:
            result = emit_local(row.event_name, **(row.payload or {}))
            if inspect.isawaitable(result):
                await result
        except Exception as exc:
            attempts = row.attempts + 1
            status = "dead" if attempts >= max_attempts else "failed"
            retry_at = None if status == "dead" else datetime.now(tz=timezone.utc) + timedelta(seconds=min(300, 2**attempts))
            await EventOutbox.filter(id=row.id).update(
                attempts=attempts,
                status=status,
                last_error=repr(exc),
                next_retry_at=retry_at,
                locked_at=None,
            )
            continue

        dispatched += 1
        await EventOutbox.filter(id=row.id).update(status="sent", processed_at=datetime.now(tz=timezone.utc), locked_at=None, last_error=None)

    return dispatched


def make_outbox_dispatch_task(*, interval_seconds: int = 10, limit: int = 50, max_attempts: int = 5) -> PeriodicTask:
    """Create a manifest task that dispatches outbox events periodically."""

    async def _dispatch() -> None:
        await dispatch_outbox_once(limit=limit, max_attempts=max_attempts)

    return PeriodicTask(
        name="system.outbox.dispatch",
        handler=_dispatch,
        interval_seconds=interval_seconds,
        leader_only=True,
    )
