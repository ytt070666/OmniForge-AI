from __future__ import annotations

from typing import Any

from apps.omniops.api.config import load_settings
from apps.omniops.api.demo_data import seed_demo
from apps.omniops.api.services import OmniOpsService
from apps.omniops.api.store import Store
from extensions.omnirag.mcp.reference_server import lookup_device, search_runbook

from .graph import AgentState


class OmniAgentRuntime:
    """Domain callbacks for the LangGraph learning/production composition.

    The callbacks reuse OmniOps evidence and OmniRAG verification instead of
    reimplementing a second retrieval or safety system.
    """

    def __init__(self) -> None:
        settings = load_settings()
        self.store = Store(settings.database_path)
        if settings.enable_demo_seed:
            seed_demo(self.store)
        self.service = OmniOpsService(settings, self.store)

    def classify(self, state: AgentState) -> dict[str, Any]:
        query = state.get("query", "").lower()
        if any(x in query for x in ("图", "截图", "topology", "chart", "image")):
            intent = "multimodal"
        elif any(x in query for x in ("device", "asset", "设备", "runbook", "sop")):
            intent = "tool_augmented"
        else:
            intent = "rag"
        return {"intent": intent, "max_retries": int(state.get("max_retries", 1))}

    def retrieve(self, state: AgentState) -> dict[str, Any]:
        incident = self.store.get_incident(state["incident_id"])
        if not incident:
            return {"evidence": [], "decision": "abstain"}
        return {"evidence": incident.get("evidence", [])}

    def tool(self, state: AgentState) -> dict[str, Any]:
        incident = self.store.get_incident(state["incident_id"])
        if not incident:
            return {"tool_results": []}
        rows: list[dict[str, Any]] = []
        asset_id = str(incident.get("asset_id") or "")
        if asset_id:
            rows.append({"tool": "lookup_device", "result": lookup_device(asset_id), "risk": "read"})
        if state.get("intent") == "tool_augmented":
            rows.append({"tool": "search_runbook", "result": search_runbook(state.get("query", "")), "risk": "read"})
        return {"tool_results": rows}

    def generate(self, state: AgentState) -> dict[str, Any]:
        incident = self.store.get_incident(state["incident_id"])
        if not incident:
            return {"answer": "现有事件不存在。"}
        evidence = state.get("evidence", [])
        question = state.get("query") or f"分析 {incident['title']}"
        if self.service.ragflow:
            try:
                result = self.service.ragflow.chat(self.service._incident_prompt(incident, evidence, question))
                return {"answer": result.answer}
            except Exception:
                pass
        return {"answer": self.service._demo_answer(incident, evidence, question)}

    def verify(self, state: AgentState) -> dict[str, Any]:
        verification = self.service._verify(state.get("answer", ""), state.get("evidence", []))
        return {"verification": verification}
