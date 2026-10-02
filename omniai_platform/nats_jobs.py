from __future__ import annotations

import asyncio
import json
from typing import Any
from uuid import uuid4

from .contracts import AnalysisStatus, utcnow


class NatsJobManager:
    """NATS-backed dispatch with process-local status tracking.

    Dispatch is distributed; status persistence is intentionally not durable in
    this learning implementation. A production exercise can move status to
    Redis/PostgreSQL without changing the public REST contract.
    """

    def __init__(self, url: str):
        self.url = url
        self._nc = None
        self._jobs: dict[str, AnalysisStatus] = {}
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        try:
            import nats
        except ImportError as exc:
            raise RuntimeError("nats-py is required for OMNIAI_JOB_BACKEND=nats") from exc
        self._nc = await nats.connect(self.url)
        await self._nc.subscribe("omniai.analysis.completed", cb=self._on_event)
        await self._nc.subscribe("omniai.analysis.failed", cb=self._on_event)

    async def close(self) -> None:
        if self._nc is not None:
            await self._nc.drain()
            self._nc = None

    async def submit(self, *, incident_id: str, query: str, max_retries: int = 1, trace_id: str = "") -> AnalysisStatus:
        if self._nc is None:
            raise RuntimeError("NATS job manager has not been started")
        run_id = f"JOB-{uuid4().hex[:12].upper()}"
        now = utcnow()
        job = AnalysisStatus(run_id=run_id, state="queued", incident_id=incident_id, created_at=now, updated_at=now)
        async with self._lock:
            self._jobs[run_id] = job
        event = {
            "event_id": uuid4().hex,
            "event_type": "analysis.requested",
            "trace_id": trace_id or uuid4().hex,
            "payload": {
                "run_id": run_id,
                "incident_id": incident_id,
                "query": query,
                "max_retries": max_retries,
            },
        }
        await self._nc.publish("omniai.analysis.requested", json.dumps(event, ensure_ascii=False).encode("utf-8"))
        async with self._lock:
            self._jobs[run_id] = job.model_copy(update={"state": "running", "updated_at": utcnow()})
            return self._jobs[run_id]

    async def _on_event(self, msg) -> None:
        try:
            event = json.loads(msg.data.decode("utf-8"))
            payload = event.get("payload") or {}
            run_id = str(payload.get("run_id") or "")
            if not run_id:
                return
            async with self._lock:
                current = self._jobs.get(run_id)
                if not current:
                    return
                if event.get("event_type") == "analysis.completed":
                    self._jobs[run_id] = current.model_copy(
                        update={"state": "completed", "updated_at": utcnow(), "result": payload.get("result") or {}}
                    )
                else:
                    self._jobs[run_id] = current.model_copy(
                        update={"state": "failed", "updated_at": utcnow(), "error": str(payload.get("error") or "worker failure")}
                    )
        except Exception:
            # Malformed events are ignored rather than poisoning the subscription.
            return

    async def get(self, run_id: str) -> AnalysisStatus | None:
        async with self._lock:
            return self._jobs.get(run_id)
