from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import Awaitable, Callable
from uuid import uuid4

from .contracts import AnalysisStatus, utcnow


class LocalJobManager:
    """Local asynchronous job manager used for Windows/demo learning mode.

    Distributed mode publishes the same contract to NATS; this local manager is
    intentionally explicit rather than pretending to be a distributed queue.
    """

    def __init__(self):
        self._jobs: dict[str, AnalysisStatus] = {}
        self._lock = asyncio.Lock()

    async def submit(self, incident_id: str, worker: Callable[[str], Awaitable[dict]]) -> AnalysisStatus:
        run_id = f"JOB-{uuid4().hex[:12].upper()}"
        now = utcnow()
        status = AnalysisStatus(run_id=run_id, state="queued", incident_id=incident_id, created_at=now, updated_at=now)
        async with self._lock:
            self._jobs[run_id] = status
        asyncio.create_task(self._execute(run_id, worker))
        return status

    async def _execute(self, run_id: str, worker: Callable[[str], Awaitable[dict]]) -> None:
        async with self._lock:
            current = self._jobs[run_id]
            self._jobs[run_id] = current.model_copy(update={"state": "running", "updated_at": utcnow()})
        try:
            result = await worker(run_id)
            async with self._lock:
                current = self._jobs[run_id]
                self._jobs[run_id] = current.model_copy(update={"state": "completed", "updated_at": utcnow(), "result": result})
        except Exception as exc:
            async with self._lock:
                current = self._jobs[run_id]
                self._jobs[run_id] = current.model_copy(update={"state": "failed", "updated_at": utcnow(), "error": f"{type(exc).__name__}: {exc}"})

    async def get(self, run_id: str) -> AnalysisStatus | None:
        async with self._lock:
            return self._jobs.get(run_id)
