from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from omniai_platform.http_contract import install_http_contract

from .graph import AgentState, build_graph
from .runtime import OmniAgentRuntime

app = FastAPI(title="OmniAI LangGraph Agent Service", version="1.0.0")
install_http_contract(app)
runtime = OmniAgentRuntime()


class AgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    incident_id: str = Field(min_length=1)
    query: str = Field(min_length=1, max_length=4000)
    max_retries: int = Field(default=1, ge=0, le=3)


@app.get("/health")
def health():
    try:
        import langgraph  # noqa: F401
        installed = True
    except ImportError:
        installed = False
    return {"ok": True, "service": "omniai-agent", "version": app.version, "framework": "LangGraph", "installed": installed}


@app.post("/api/v1/agent/run")
def run_agent(payload: AgentRequest):
    try:
        graph = build_graph(
            classify=runtime.classify,
            retrieve=runtime.retrieve,
            tool=runtime.tool,
            generate=runtime.generate,
            verify=runtime.verify,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    state: AgentState = {
        "incident_id": payload.incident_id,
        "query": payload.query,
        "retry_count": 0,
        "max_retries": payload.max_retries,
    }
    result = graph.invoke(state)
    return result
