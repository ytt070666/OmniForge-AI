from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ModuleDescriptor(StrictModel):
    id: str
    name: str
    role: str
    runtime: str
    status: Literal["available", "optional", "external", "not_configured"]
    upstream: str | None = None
    license: str | None = None
    endpoint: str | None = None


class AnalysisRequest(StrictModel):
    incident_id: str = Field(min_length=1, max_length=128)
    question: str | None = Field(default=None, max_length=4000)


class AgentRunRequest(StrictModel):
    incident_id: str = Field(min_length=1, max_length=128)
    query: str = Field(min_length=1, max_length=4000)
    max_retries: int = Field(default=1, ge=0, le=3)


class AnalysisStatus(StrictModel):
    run_id: str
    state: Literal["queued", "running", "completed", "failed"]
    incident_id: str
    created_at: str
    updated_at: str
    result: dict[str, Any] | None = None
    error: str | None = None


class ChatRequest(StrictModel):
    message: str = Field(min_length=1, max_length=8000)


class IncidentCreate(StrictModel):
    title: str = Field(min_length=1, max_length=240)
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    asset_id: str = Field(default="", max_length=128)
    summary: str = Field(default="", max_length=4000)


class EventEnvelope(StrictModel):
    event_id: str = Field(default_factory=lambda: uuid4().hex)
    event_type: str
    trace_id: str
    source: str
    created_at: str = Field(default_factory=utcnow)
    payload: dict[str, Any]
