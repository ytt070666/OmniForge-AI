"""Compile a safe TaskSpec into RAGFlow's native Canvas DSL."""

from __future__ import annotations

import copy
import re
from typing import Any

from .schema import TaskSpec
from .validator import validate_taskspec

_REF_RE = re.compile(r"\$\{([^}]+)\}")
_KIND_TO_COMPONENT = {"retrieval": "Retrieval", "agent": "Agent", "message": "Message"}
_KIND_TO_NODE_TYPE = {"retrieval": "ragNode", "agent": "agentNode", "message": "messageNode"}


def _component_id(step_id: str, kind: str) -> str:
    return f"{_KIND_TO_COMPONENT[kind]}:Omni_{step_id}"


def _compile_string(value: str, id_map: dict[str, str]) -> str:
    def repl(match: re.Match[str]) -> str:
        raw = match.group(1).strip()
        if raw.startswith("sys."):
            return "{" + raw + "}"
        step_id, output = raw.split(".", 1)
        return "{" + id_map[step_id] + "@" + output + "}"

    return _REF_RE.sub(repl, value)


def _compile_value(value: Any, id_map: dict[str, str]) -> Any:
    if isinstance(value, str):
        return _compile_string(value, id_map)
    if isinstance(value, list):
        return [_compile_value(x, id_map) for x in value]
    if isinstance(value, dict):
        return {k: _compile_value(v, id_map) for k, v in value.items()}
    return copy.deepcopy(value)


def _retrieval_params(params: dict[str, Any]) -> dict[str, Any]:
    out = {
        "dataset_ids": [],
        "query": "{sys.query}",
        "similarity_threshold": 0.2,
        "keywords_similarity_weight": 0.5,
        "top_n": 8,
        "rerank_candidates_count": 64,
        "rerank_id": "",
        "cross_languages": [],
        "use_kg": False,
        "toc_enhance": False,
        "empty_response": "",
        "outputs": {"formalized_content": {"type": "string", "value": ""}},
    }
    out.update(params)
    return out


def _agent_params(params: dict[str, Any]) -> dict[str, Any]:
    out = {
        "llm_id": "",
        "sys_prompt": "You are a careful assistant. Use configured tools only when they are needed.",
        "user_prompt": "{sys.query}",
        "description": "",
        "max_rounds": 5,
        "max_retries": 2,
        "temperature": 0.1,
        "temperatureEnabled": False,
        "cite": True,
        "mcp": [],
        "tools": [],
        "prompts": [],
        "outputs": {"content": {"type": "string", "value": ""}},
    }
    out.update(params)
    user_prompt = str(out.pop("user_prompt", "{sys.query}"))
    out["prompts"] = [{"role": "user", "content": user_prompt}]
    return out


def _message_params(params: dict[str, Any]) -> dict[str, Any]:
    out = {"content": [], "stream": True}
    out.update(params)
    if isinstance(out["content"], str):
        out["content"] = [out["content"]]
    return out


def compile_taskspec(spec: TaskSpec) -> dict[str, Any]:
    validate_taskspec(spec)
    id_map = {step.id: _component_id(step.id, step.kind) for step in spec.steps}
    step_by_id = {step.id: step for step in spec.steps}

    downstream: dict[str, list[str]] = {step.id: [] for step in spec.steps}
    for step in spec.steps:
        for dep in step.depends_on:
            downstream[dep].append(step.id)

    roots = [step for step in spec.steps if not step.depends_on]
    components: dict[str, Any] = {
        "begin": {
            "obj": {
                "component_name": "Begin",
                "params": {"enablePrologue": False, "inputs": {}, "mode": "conversational", "prologue": ""},
            },
            "downstream": [id_map[step.id] for step in roots],
            "upstream": [],
        }
    }

    graph_nodes = [
        {
            "id": "begin",
            "type": "beginNode",
            "position": {"x": 0, "y": 0},
            "data": {"label": "Begin", "name": "begin"},
        }
    ]
    graph_edges: list[dict[str, Any]] = []
    for root in roots:
        cid = id_map[root.id]
        graph_edges.append(
            {
                "id": f"omni-edge__begin-{cid}",
                "source": "begin",
                "sourceHandle": "start",
                "target": cid,
                "targetHandle": "end",
            }
        )

    for idx, step in enumerate(spec.steps, start=1):
        cid = id_map[step.id]
        compiled_params = _compile_value(step.params, id_map)
        if step.kind == "retrieval":
            params = _retrieval_params(compiled_params)
        elif step.kind == "agent":
            params = _agent_params(compiled_params)
        else:
            params = _message_params(compiled_params)

        upstream = [id_map[d] for d in step.depends_on] or ["begin"]
        components[cid] = {
            "obj": {"component_name": _KIND_TO_COMPONENT[step.kind], "params": params},
            "upstream": upstream,
            "downstream": [id_map[d] for d in downstream[step.id]],
        }
        graph_nodes.append(
            {
                "id": cid,
                "type": _KIND_TO_NODE_TYPE[step.kind],
                "position": {"x": idx * 260, "y": (idx % 3) * 160},
                "data": {"label": _KIND_TO_COMPONENT[step.kind], "name": step.id, "form": copy.deepcopy(params)},
            }
        )
        for dep in step.depends_on:
            source = id_map[dep]
            graph_edges.append(
                {
                    "id": f"omni-edge__{source}-{cid}",
                    "source": source,
                    "sourceHandle": "start",
                    "target": cid,
                    "targetHandle": "end",
                }
            )

    return {
        "components": components,
        "history": [],
        "path": [],
        "retrieval": [],
        "memory": [],
        "globals": {
            "sys.query": "",
            "sys.user_id": "",
            "sys.conversation_turns": 0,
            "sys.files": [],
            "sys.history": [],
            "sys.date": "",
        },
        "variables": {},
        "graph": {"nodes": graph_nodes, "edges": graph_edges},
        "omnirag_taskspec": {
            "version": spec.version,
            "name": spec.name,
            "description": spec.description,
            "step_id_map": id_map,
        },
    }
