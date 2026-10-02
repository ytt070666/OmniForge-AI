"""Exercise the installed LangGraph graph with three deterministic paths."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from services.omniai_agent.graph import build_graph


def classify(state):
    return {"intent": "rag"}


def retrieve(state):
    return {"evidence": [{"id": "E-1", "text": "DNS timeout"}]}


def tool(state):
    return {"tool_results": [{"tool": "lookup_device", "risk": "read"}]}


def generate(state):
    return {"answer": "GW-01 DNS timeout", "retry_count": state.get("retry_count", 0)}


def verify(state):
    if state["query"] == "retry" and state.get("retry_count", 0) == 0:
        decision = "retrieve_more"
    elif state["query"] == "abstain":
        decision = "abstain"
    else:
        decision = "pass"
    return {"verification": {"decision": decision}}


def main() -> None:
    graph = build_graph(
        classify=classify, retrieve=retrieve, tool=tool,
        generate=generate, verify=verify,
    )
    results = {}
    for name in ("pass", "retry", "abstain"):
        state = graph.invoke({"query": name, "retry_count": 0, "max_retries": 1})
        results[name] = {"decision": state["decision"], "retry_count": state["retry_count"]}
    assert results == {
        "pass": {"decision": "pass", "retry_count": 0},
        "retry": {"decision": "pass", "retry_count": 1},
        "abstain": {"decision": "abstain", "retry_count": 0},
    }
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
