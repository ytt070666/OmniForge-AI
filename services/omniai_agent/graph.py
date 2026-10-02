from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal, TypedDict


class AgentState(TypedDict, total=False):
    query: str
    incident_id: str
    intent: str
    evidence: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    answer: str
    verification: dict[str, Any]
    retry_count: int
    max_retries: int
    decision: str


RuntimeFn = Callable[[AgentState], dict[str, Any]]


def route_after_verify(state: AgentState) -> Literal["retry", "finish"]:
    decision = str((state.get("verification") or {}).get("decision") or state.get("decision") or "abstain")
    retries = int(state.get("retry_count", 0))
    max_retries = int(state.get("max_retries", 1))
    if decision == "retrieve_more" and retries < max_retries:
        return "retry"
    return "finish"


def final_decision(state: AgentState) -> str:
    verification = state.get("verification") or {}
    decision = str(verification.get("decision") or state.get("decision") or "abstain")
    if decision == "retrieve_more" and int(state.get("retry_count", 0)) >= int(state.get("max_retries", 1)):
        return "abstain"
    return decision


def build_graph(
    *,
    classify: RuntimeFn,
    retrieve: RuntimeFn,
    tool: RuntimeFn,
    generate: RuntimeFn,
    verify: RuntimeFn,
):
    """Build the real LangGraph workflow with injected domain callbacks.

    Importing LangGraph is intentionally delayed so the repository can still run
    static/demo validation before the isolated agent environment is installed.
    """
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:  # pragma: no cover - depends on optional env
        raise RuntimeError("LangGraph is not installed. Install services/omniai_agent/requirements.txt") from exc

    graph = StateGraph(AgentState)
    graph.add_node("classify", classify)
    graph.add_node("retrieve", retrieve)
    graph.add_node("tool", tool)
    graph.add_node("generate", generate)
    graph.add_node("verify", verify)
    graph.add_node("retry", lambda state: {"retry_count": int(state.get("retry_count", 0)) + 1})
    graph.add_node("finish", lambda state: {"decision": final_decision(state)})

    graph.add_edge(START, "classify")
    graph.add_edge("classify", "retrieve")
    graph.add_edge("retrieve", "tool")
    graph.add_edge("tool", "generate")
    graph.add_edge("generate", "verify")
    graph.add_conditional_edges("verify", route_after_verify, {"retry": "retry", "finish": "finish"})
    graph.add_edge("retry", "retrieve")
    graph.add_edge("finish", END)
    return graph.compile()
