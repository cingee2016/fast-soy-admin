from __future__ import annotations

import asyncio
import inspect
from contextlib import suppress

from app.core.business import PeriodicTask
from app.core.log import log


class BusinessTaskRunner:
    """Run manifest-declared periodic business tasks."""

    def __init__(self, tasks: list[PeriodicTask], *, redis=None, lock_prefix: str = "business:task") -> None:
        self.tasks = tasks
        self.redis = redis
        self.lock_prefix = lock_prefix
        self._running: list[asyncio.Task] = []
        self._stop = asyncio.Event()

    def start(self) -> None:
        if self._running or not self.tasks:
            return
        self._stop.clear()
        self._running = [asyncio.create_task(self._run_task(task), name=f"business-task:{task.name}") for task in self.tasks]
        log.info(f"Business tasks started: {len(self._running)}")

    async def stop(self) -> None:
        if not self._running:
            return
        self._stop.set()
        for task in self._running:
            task.cancel()
        await asyncio.gather(*self._running, return_exceptions=True)
        self._running = []
        log.info("Business tasks stopped")

    async def _run_task(self, task: PeriodicTask) -> None:
        if task.run_immediately:
            await self._run_once(task)
        while not self._stop.is_set():
            with suppress(asyncio.TimeoutError):
                await asyncio.wait_for(self._stop.wait(), timeout=task.interval_seconds)
            if self._stop.is_set():
                return
            await self._run_once(task)

    async def _run_once(self, task: PeriodicTask) -> None:
        if task.leader_only and self.redis is not None:
            lock_key = f"{self.lock_prefix}:{task.name}"
            ttl = max(task.interval_seconds, 10)
            acquired = await self.redis.set(lock_key, "1", nx=True, ex=ttl)
            if not acquired:
                return
        try:
            result = task.handler()
            if inspect.isawaitable(result):
                await result
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception(f"Business task failed: {task.name}")
