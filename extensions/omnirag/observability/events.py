"""Privacy-reduced structured trace events for OmniRAG extensions.

RAGFlow already owns native Langfuse tracing. This module does not create a
second tracing backend; it defines extension-level metrics that can later be
attached to the same trace/session IDs without storing prompts, completions,
retrieved text, or raw tool arguments by default.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

_ALLOWED_STATUS = {"ok", "error", "denied", "abstain", "retry"}


def hash_identifier(value: str | None) -> str | None:
    if not value:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]


@dataclass(frozen=True)
class TraceEvent:
    trace_id: str
    component: str
    operation: str
    status: str
    latency_ms: float
    timestamp_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    session_id_hash: str | None = None
    model: str | None = None
    query_class: str | None = None
    tool_name: str | None = None
    tool_risk: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    retrieval_candidates: int | None = None
    tool_calls: int | None = None
    tool_failures: int | None = None
    retry_count: int | None = None
    abstained: bool | None = None
    tags: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in _ALLOWED_STATUS:
            raise ValueError(f"unsupported status: {self.status}")
        if self.latency_ms < 0:
            raise ValueError("latency_ms must be non-negative")
        for key in ("input_tokens", "output_tokens", "retrieval_candidates", "tool_calls", "tool_failures", "retry_count"):
            value = getattr(self, key)
            if value is not None and value < 0:
                raise ValueError(f"{key} must be non-negative")
        # Tags are low-cardinality labels only. Long values are likely data, not
        # metrics metadata, and are rejected rather than silently logged.
        for key, value in self.tags.items():
            if len(key) > 64 or len(value) > 96:
                raise ValueError("trace tags must be low-cardinality metadata")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def new_trace_id() -> str:
    return uuid.uuid4().hex


class JsonlTraceRecorder:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event: TraceEvent) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.as_dict(), ensure_ascii=False, sort_keys=True) + "\n")
