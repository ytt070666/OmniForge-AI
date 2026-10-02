from __future__ import annotations

import asyncio
import base64
import binascii
import json
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, Header, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from apps.omniops.api.config import load_settings as load_omniops_settings
from apps.omniops.api.demo_data import seed_demo
from apps.omniops.api.services import OmniOpsService
from apps.omniops.api.store import Store
from omniai_platform.contracts import AgentRunRequest, AnalysisRequest, ChatRequest, IncidentCreate
from omniai_platform.idempotency import InMemoryIdempotencyStore
from omniai_platform.jobs import LocalJobManager
from omniai_platform.modules import default_modules
from omniai_platform.nats_jobs import NatsJobManager
from omniai_platform.rate_limit import SlidingWindowLimiter
from omniai_platform.resilience import AsyncConcurrencyGate

from .settings import load_gateway_settings

try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
except Exception:  # pragma: no cover - optional in stripped learning envs
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4"
    Counter = Histogram = generate_latest = None  # type: ignore[assignment]


class Runtime:
    def __init__(self) -> None:
        self.gateway = load_gateway_settings()
        self.omniops = load_omniops_settings()
        self.store = Store(self.omniops.database_path)
        if self.omniops.enable_demo_seed:
            seed_demo(self.store)
        self.service = OmniOpsService(self.omniops, self.store)
        self.jobs = LocalJobManager()
        self.nats_jobs: NatsJobManager | None = None
        self.idempotency = InMemoryIdempotencyStore()
        self.rate_limit = SlidingWindowLimiter(self.gateway.rate_limit_per_minute, 60.0)
        self.agent_gate = AsyncConcurrencyGate(self.gateway.agent_concurrency)


runtime = Runtime()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if runtime.gateway.job_backend == "nats":
        runtime.nats_jobs = NatsJobManager(runtime.gateway.nats_url)
        await runtime.nats_jobs.start()
    try:
        yield
    finally:
        if runtime.nats_jobs is not None:
            await runtime.nats_jobs.close()
            runtime.nats_jobs = None


app = FastAPI(
    title="OmniAI Platform Gateway",
    version="2.0.0",
    description="FastAPI REST/OpenAPI gateway over OmniOps, OmniRAG and optional modular AI services.",
    lifespan=lifespan,
)


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": f"HTTP_{exc.status_code}", "message": str(exc.detail), "request_id": getattr(request.state, "request_id", "")}},
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, _exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "VALIDATION_ERROR", "message": "request validation failed", "request_id": getattr(request.state, "request_id", "")}},
    )

if os.getenv("OMNIAI_OTEL_CONSOLE", "").lower() in {"1", "true", "yes"}:
    from opentelemetry import trace
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)

_REQUESTS = Counter("omniai_http_requests_total", "HTTP requests", ["method", "path", "status"]) if Counter else None
_LATENCY = Histogram("omniai_http_request_seconds", "HTTP request latency", ["method", "path"]) if Histogram else None


@app.middleware("http")
async def request_governance(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    request.state.request_id = request_id
    if os.getenv("OMNIAI_OTEL_CONSOLE", "").lower() in {"1", "true", "yes"}:
        from opentelemetry import trace

        trace.get_current_span().set_attribute("request.id", request_id)
    client_key = request.client.host if request.client else "unknown"
    if not await runtime.rate_limit.allow(client_key):
        response = JSONResponse(
            status_code=429,
            content={"error": {"code": "RATE_LIMITED", "message": "request rate limit exceeded", "request_id": request_id}},
        )
        response.headers["X-Request-ID"] = request_id
        return response
    started = asyncio.get_running_loop().time()
    try:
        response = await call_next(request)
    except Exception as exc:  # FastAPI validation errors are handled before this branch.
        response = JSONResponse(
            status_code=500,
            content={"error": {"code": "INTERNAL_ERROR", "message": type(exc).__name__, "request_id": request_id}},
        )
    elapsed = asyncio.get_running_loop().time() - started
    response.headers["X-Request-ID"] = request_id
    if _REQUESTS:
        _REQUESTS.labels(request.method, request.url.path, str(response.status_code)).inc()
    if _LATENCY:
        _LATENCY.labels(request.method, request.url.path).observe(elapsed)
    return response


@app.get("/api/v1/health")
async def health() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "omniai-gateway",
        "version": app.version,
        "product": "OmniAI Platform / OmniOps Copilot",
        "runtime": runtime.service.runtime_status(),
        "gateway": {"framework": "FastAPI", "agent_concurrency": runtime.gateway.agent_concurrency},
    }


@app.get("/api/v1/platform/modules")
async def modules() -> dict[str, Any]:
    return {"items": [item.model_dump() for item in default_modules()]}


@app.post("/api/v1/agent/run")
async def run_agent(payload: AgentRunRequest, request: Request) -> dict[str, Any]:
    """Reach the optional LangGraph service through the product gateway."""
    base_url = os.getenv("OMNIAI_AGENT_URL", "").rstrip("/")
    if not base_url:
        raise HTTPException(status_code=503, detail="LangGraph agent service is not configured")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{base_url}/api/v1/agent/run",
                json=payload.model_dump(),
                headers={"X-Request-ID": request.state.request_id},
            )
            response.raise_for_status()
            return response.json()
    except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"LangGraph agent service failed: {type(exc).__name__}") from exc


@app.get("/api/v1/overview")
async def overview() -> dict[str, Any]:
    return await asyncio.to_thread(runtime.service.overview)


@app.get("/api/v1/incidents")
async def list_incidents() -> dict[str, Any]:
    return {"items": await asyncio.to_thread(runtime.store.list_incidents)}


@app.post("/api/v1/incidents", status_code=201)
async def create_incident(payload: IncidentCreate) -> dict[str, Any]:
    return await asyncio.to_thread(runtime.store.create_incident, payload.title, payload.severity, payload.asset_id, payload.summary)


@app.get("/api/v1/incidents/{incident_id}")
async def get_incident(incident_id: str) -> dict[str, Any]:
    item = await asyncio.to_thread(runtime.store.get_incident, incident_id)
    if not item:
        raise HTTPException(status_code=404, detail="incident not found")
    return item


async def _analysis_worker(payload: AnalysisRequest) -> dict[str, Any]:
    async def run() -> dict[str, Any]:
        result = await asyncio.to_thread(runtime.service.analyze_incident, payload.incident_id, payload.question)
        return result.__dict__

    return await runtime.agent_gate.run(run)


@app.post("/api/v1/analyses", status_code=status.HTTP_202_ACCEPTED)
async def submit_analysis(payload: AnalysisRequest, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")) -> dict[str, Any]:
    if not await asyncio.to_thread(runtime.store.get_incident, payload.incident_id):
        raise HTTPException(status_code=404, detail="incident not found")
    if idempotency_key:
        existing = await runtime.idempotency.get(idempotency_key)
        if existing:
            return existing
    if runtime.gateway.job_backend == "nats":
        if runtime.nats_jobs is None:
            raise HTTPException(status_code=503, detail="NATS job backend is not connected")
        job = await runtime.nats_jobs.submit(
            incident_id=payload.incident_id,
            query=payload.question or f"分析 {payload.incident_id} 的最可能原因、证据和下一步建议。",
            max_retries=1,
        )
    else:
        job = await runtime.jobs.submit(payload.incident_id, lambda _job_id: _analysis_worker(payload))
    response = job.model_dump()
    if idempotency_key:
        await runtime.idempotency.put(idempotency_key, response)
    return response


@app.get("/api/v1/analyses/{run_id}")
async def get_analysis(run_id: str) -> dict[str, Any]:
    manager = runtime.nats_jobs if runtime.gateway.job_backend == "nats" else runtime.jobs
    if manager is None:
        raise HTTPException(status_code=503, detail="job backend is unavailable")
    job = await manager.get(run_id)
    if not job:
        raise HTTPException(status_code=404, detail="analysis job not found")
    return job.model_dump()


@app.get("/api/v1/analyses/{run_id}/events")
async def analysis_events(run_id: str) -> StreamingResponse:
    manager = runtime.nats_jobs if runtime.gateway.job_backend == "nats" else runtime.jobs
    if manager is None or not await manager.get(run_id):
        raise HTTPException(status_code=404, detail="analysis job not found")

    async def stream():
        last_state = None
        for _ in range(600):
            job = await manager.get(run_id)
            if not job:
                break
            if job.state != last_state or job.state in {"completed", "failed"}:
                yield f"event: analysis\ndata: {json.dumps(job.model_dump(), ensure_ascii=False)}\n\n"
                last_state = job.state
            if job.state in {"completed", "failed"}:
                break
            await asyncio.sleep(0.25)

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.post("/api/v1/chat")
async def chat(payload: ChatRequest) -> dict[str, Any]:
    return await runtime.agent_gate.run(lambda: asyncio.to_thread(runtime.service.chat, payload.message))


@app.get("/api/v1/chat/history")
async def chat_history() -> dict[str, Any]:
    return {"items": await asyncio.to_thread(runtime.store.chat_history)}


@app.get("/api/v1/evidence")
async def evidence(incident_id: str = "") -> dict[str, Any]:
    sql = "SELECT * FROM evidence"
    params: tuple[Any, ...] = ()
    if incident_id:
        sql += " WHERE incident_id=?"
        params = (incident_id,)
    rows = await asyncio.to_thread(runtime.store.query, sql + " ORDER BY created_at", params)
    return {"items": rows}


@app.get("/api/v1/traces")
async def traces(incident_id: str = "") -> dict[str, Any]:
    if incident_id:
        rows = await asyncio.to_thread(runtime.store.query, "SELECT * FROM agent_runs WHERE incident_id=? ORDER BY created_at DESC", (incident_id,))
    else:
        rows = await asyncio.to_thread(runtime.store.query, "SELECT * FROM agent_runs ORDER BY created_at DESC LIMIT 30")
    for row in rows:
        row["steps"] = await asyncio.to_thread(runtime.store.query, "SELECT * FROM trace_steps WHERE run_id=? ORDER BY step_no", (row["id"],))
    return {"items": rows}


@app.get("/api/v1/tools")
async def tools() -> dict[str, Any]:
    audits = await asyncio.to_thread(runtime.store.query, "SELECT * FROM tool_audit ORDER BY created_at DESC LIMIT 30")
    return {
        "policy": {"default": "fail-closed", "read": "allow", "write": "deny", "execute": "deny", "unknown": "deny"},
        "tools": [
            {"name": "lookup_device", "source": "MCP", "risk": "read", "status": "available"},
            {"name": "search_runbook", "source": "MCP", "risk": "read", "status": "available"},
            {"name": "calculate_availability", "source": "MCP", "risk": "read", "status": "available"},
            {"name": "update_asset", "source": "example", "risk": "write", "status": "blocked_by_default"},
            {"name": "execute_python", "source": "example", "risk": "execute", "status": "blocked_by_default"},
        ],
        "audit": audits,
    }


@app.get("/api/v1/knowledge")
async def knowledge() -> dict[str, Any]:
    return {"items": await asyncio.to_thread(runtime.store.query, "SELECT * FROM knowledge_assets ORDER BY created_at DESC")}


@app.post("/api/v1/knowledge/upload", status_code=201)
async def upload_knowledge(request: Request) -> dict[str, Any]:
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON object required")
    name = str(body.get("name") or "").strip()
    data_url = str(body.get("data") or "")
    if not name or not data_url:
        raise HTTPException(status_code=400, detail="name and data are required")
    if "," in data_url:
        data_url = data_url.split(",", 1)[1]
    try:
        raw = base64.b64decode(data_url, validate=True)
        return await asyncio.to_thread(runtime.service.upload_asset, name, str(body.get("kind") or ""), raw)
    except (ValueError, binascii.Error) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v1/evaluation")
async def evaluation() -> dict[str, Any]:
    return {"items": await asyncio.to_thread(runtime.store.query, "SELECT * FROM evaluation_metrics ORDER BY category,key")}


@app.post("/api/v1/demo/reset")
async def reset_demo() -> dict[str, bool]:
    await asyncio.to_thread(seed_demo, runtime.store, True)
    return {"ok": True}


@app.get("/metrics")
async def metrics() -> Response:
    if not generate_latest:
        raise HTTPException(status_code=503, detail="prometheus-client is not installed")
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Serve the existing OmniOps UI through the gateway. API routes are registered
# first so this catch-all never shadows /api/v1 or /metrics.
_static = runtime.gateway.static_root
if (_static / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=_static / "assets"), name="omniops-assets")


@app.get("/{path:path}", include_in_schema=False)
async def spa(path: str):
    candidate = (_static / path).resolve() if path else (_static / "index.html").resolve()
    if _static.resolve() not in candidate.parents and candidate != _static.resolve():
        raise HTTPException(status_code=403, detail="forbidden")
    if candidate.is_file():
        return FileResponse(candidate)
    return FileResponse(_static / "index.html")
