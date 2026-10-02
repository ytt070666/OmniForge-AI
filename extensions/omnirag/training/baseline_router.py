"""Transparent rule baseline for Phase-6 router research.

This baseline is deliberately not a replacement for Phase-2/3/5 runtime policy.
It only gives the learned router a reproducible comparison point.
"""

from __future__ import annotations

from extensions.omnirag.retrieval.query_features import extract_query_features
from .schema import make_completion


def _tool_intent(query: str) -> str | None:
    q = query.lower()
    # Require action-like wording so conceptual questions about MCP/tools do not
    # accidentally become tool calls.
    if any(x in q for x in ("weather forecast", "天气预报", "查询天气", "天气")) and any(x in q for x in ("forecast", "查询", "what is", "use")):
        return "weather"
    if ("asset" in q or "资产" in q) and any(x in q for x in ("look up", "lookup", "查询", "retrieve", "use")):
        return "device_lookup"
    if ("runbook" in q or "排查手册" in q) and any(x in q for x in ("search", "find", "查找", "use")):
        return "runbook_search"
    if ("availability" in q or "可用率" in q) and any(x in q for x in ("calculate", "compute", "计算")):
        return "availability_calc"
    if ("knowledge base" in q or "知识库" in q) and any(x in q for x in ("search", "find", "查询", "检索", "use")):
        return "knowledge_search"
    return None


def predict(query: str) -> str:
    tool = _tool_intent(query)
    if tool:
        return make_completion(
            query_class="tool",
            retrieval_profile="balanced",
            needs_tools=True,
            tool_intent=tool,
            evidence_strictness="high",
        )

    f = extract_query_features(query)
    if f.visual_signal:
        return make_completion(query_class="visual", retrieval_profile="balanced", needs_visual=True, evidence_strictness="high")
    if f.contains_cjk:
        return make_completion(query_class="crosslingual", retrieval_profile="dense_heavy")
    if (f.contains_identifier or f.lexical_signal or f.contains_quoted_phrase) and f.semantic_signal:
        return make_completion(query_class="hybrid", retrieval_profile="balanced", evidence_strictness="high")
    if f.contains_identifier or f.lexical_signal or f.contains_quoted_phrase:
        return make_completion(query_class="lexical_precision", retrieval_profile="sparse_heavy", evidence_strictness="high")
    return make_completion(query_class="semantic", retrieval_profile="dense_heavy")
