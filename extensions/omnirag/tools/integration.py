"""Minimal, feature-flagged integration with RAGFlow's Agent component."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .policy import governance_enabled, policy_from_env
from .registry import ToolRegistry
from .selector import ToolSelectorV1
from .session import GovernedToolCallSession


def _selection_query(agent: object, user_prompt_text: str) -> str:
    if user_prompt_text.strip():
        return user_prompt_text.strip()
    canvas = getattr(agent, "_canvas", None)
    globals_ = getattr(canvas, "globals", {}) if canvas is not None else {}
    query = globals_.get("sys.query", "") if isinstance(globals_, dict) else ""
    if isinstance(query, str) and query.strip():
        return query.strip()
    prompts = getattr(getattr(agent, "_param", None), "prompts", []) or []
    text = "\n".join(str(p.get("content") or "") for p in prompts if isinstance(p, dict))
    return text[:4000]


def prepare_agent_tools(agent: object, user_prompt_text: str = "") -> dict[str, Any]:
    """Rebind only a safe, relevant subset for the current Agent invocation.

    When the feature flag is off this function is a strict no-op.
    """

    if not governance_enabled():
        # Defensive runtime toggle support: if a previous turn used governance,
        # restore the original full binding instead of leaving a stale shortlist.
        if hasattr(agent, "_omnirag_full_tool_meta") and hasattr(agent, "_omnirag_base_tool_session"):
            full_meta = getattr(agent, "_omnirag_full_tool_meta", []) or []
            base = getattr(agent, "_omnirag_base_tool_session", None)
            if base is not None and full_meta:
                agent.chat_mdl.bind_tools(base, full_meta)
        return {"enabled": False, "reason": "OMNIRAG_TOOL_GOVERNANCE is disabled"}

    tools = getattr(agent, "tools", {}) or {}
    tool_meta = getattr(agent, "tool_meta", []) or []
    if not tools or not tool_meta:
        return {"enabled": True, "selected": [], "reason": "no configured tools"}

    if not hasattr(agent, "_omnirag_full_tool_meta"):
        agent._omnirag_full_tool_meta = deepcopy(tool_meta)
        agent._omnirag_base_tool_session = getattr(agent, "toolcall_session", None)

    registry = ToolRegistry.from_ragflow(tools, agent._omnirag_full_tool_meta)
    policy = policy_from_env()
    query = _selection_query(agent, user_prompt_text)
    selection = ToolSelectorV1().select(query, registry, policy)

    selected_schemas = registry.schemas(selection.selected_names)
    base_session = getattr(agent, "_omnirag_base_tool_session", None)
    if base_session is None:
        raise RuntimeError("OmniRAG tool governance could not locate the original RAGFlow tool session")

    def trace_sink(trace: list[dict[str, Any]]) -> None:
        if hasattr(agent, "set_output"):
            agent.set_output("_OMNIRAG_TOOL_TRACE", trace)

    governed = GovernedToolCallSession(
        base_session=base_session,
        registry=registry,
        allowed_names=selection.selected_names,
        policy=policy,
        trace_sink=trace_sink,
    )
    agent._omnirag_tool_session = governed
    agent._omnirag_tool_registry = registry
    agent._omnirag_tool_selection = selection

    # RAGFlow's LLMBundle forwards this to the provider-specific chat model.
    # Its native bind_tools() is intentionally a no-op for an empty schema
    # list, so explicitly clear an earlier binding when policy/selection leaves
    # zero visible tools. Otherwise a previous turn could retain stale tools.
    if selected_schemas:
        agent.chat_mdl.bind_tools(governed, selected_schemas)
    else:
        mdl = getattr(agent.chat_mdl, "mdl", None)
        if mdl is not None:
            mdl.tools = []
            mdl.toolcall_session = governed

    metadata = {
        "enabled": True,
        "selector": ToolSelectorV1.name,
        "query_length": len(query),
        "selected": list(selection.selected_names),
        "rejected_by_policy": list(selection.rejected_by_policy),
        "fallback_used": selection.fallback_used,
        "scores": {k: selection.scores[k] for k in selection.selected_names},
        "policy": {
            "allowed_risks": sorted(r.value for r in policy.allowed_risks),
            "allow_destructive": policy.allow_destructive,
            "allow_open_world": policy.allow_open_world,
            "max_visible_tools": policy.max_visible_tools,
            "max_total_calls": policy.max_total_calls,
            "max_calls_per_tool": policy.max_calls_per_tool,
        },
        "inventory": registry.public_inventory(),
    }
    if hasattr(agent, "set_output"):
        agent.set_output("_OMNIRAG_TOOL_GOVERNANCE", metadata)
        agent.set_output("_OMNIRAG_TOOL_TRACE", [])
    return metadata
