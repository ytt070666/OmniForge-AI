"""Deterministic capability shortlist for large tool inventories.

This is intentionally transparent and auditable. It is a pre-selector, not a
claim that lexical scoring is superior to semantic routing. The LLM still makes
the final choice among the shortlisted schemas.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from .policy import ToolPolicy
from .registry import ToolRegistry
from .types import ToolDescriptor, ToolSelection

_WORD_RE = re.compile(r"[a-zA-Z0-9]+(?:[._/-][a-zA-Z0-9]+)*")
_CJK_RE = re.compile(r"[\u3400-\u9fff]+")

_INTENT_TERMS = {
    "search": {"search", "find", "lookup", "retrieve", "query", "检索", "搜索", "查找", "查询"},
    "weather": {"weather", "forecast", "temperature", "天气", "气温", "预报"},
    "database": {"database", "sql", "table", "row", "数据库", "表", "数据"},
    "code": {"code", "python", "javascript", "calculate", "compute", "代码", "计算", "脚本"},
    "email": {"email", "mail", "send", "邮件", "发送"},
    "web": {"web", "internet", "browser", "website", "网页", "网站", "浏览器"},
}


def tokenize(text: str) -> Counter[str]:
    text = (text or "").lower()
    tokens: list[str] = []
    for match in _WORD_RE.finditer(text):
        token = match.group(0)
        tokens.append(token)
        # Keep the full identifier but also expose its semantic parts so names
        # like `search_docs` and phrases like `knowledge-base` can match natural
        # language without a special-case vocabulary.
        parts = [part for part in re.split(r"[._/-]+", token) if part]
        if len(parts) > 1:
            tokens.extend(parts)
    for seq in _CJK_RE.findall(text):
        tokens.extend(seq)
        if len(seq) >= 2:
            tokens.extend(seq[i : i + 2] for i in range(len(seq) - 1))
    return Counter(tokens)


def _coverage(query_tokens: Counter[str], tool_tokens: Counter[str]) -> float:
    if not query_tokens or not tool_tokens:
        return 0.0
    overlap = sum(min(query_tokens[t], tool_tokens[t]) for t in query_tokens.keys() & tool_tokens.keys())
    return overlap / max(1, sum(query_tokens.values()))


def _intent_bonus(query_text: str, tool: ToolDescriptor) -> float:
    q = set(tokenize(query_text))
    t = set(tokenize(f"{tool.original_name} {tool.description}"))
    bonus = 0.0
    for words in _INTENT_TERMS.values():
        if q & words and t & words:
            bonus += 0.08
    return min(0.24, bonus)


def score_tool(query: str, tool: ToolDescriptor) -> float:
    q = tokenize(query)
    body = tokenize(f"{tool.original_name} {tool.name} {tool.description}")
    coverage = _coverage(q, body)
    name_tokens = tokenize(tool.original_name)
    name_coverage = _coverage(q, name_tokens)
    read_prior = 0.02 if tool.risk.value == "read" else 0.0
    source_prior = 0.01 if tool.source.value == "builtin" else 0.0
    score = 0.64 * coverage + 0.25 * name_coverage + _intent_bonus(query, tool) + read_prior + source_prior
    return round(min(1.0, max(0.0, score)), 6)


class ToolSelectorV1:
    name = "deterministic_capability_selector_v1"

    def select(self, query: str, registry: ToolRegistry, policy: ToolPolicy) -> ToolSelection:
        allowed: list[ToolDescriptor] = []
        rejected: list[str] = []
        scores: dict[str, float] = {}

        for tool in registry.all():
            ok, _ = policy.permits(tool)
            if not ok:
                rejected.append(tool.name)
                continue
            allowed.append(tool)
            scores[tool.name] = score_tool(query, tool)

        if not allowed:
            return ToolSelection(query=query, selected_names=(), rejected_by_policy=tuple(sorted(rejected)), scores=scores)

        ranked = sorted(allowed, key=lambda t: (-scores[t.name], t.name))
        selected = [t for t in ranked if scores[t.name] >= policy.selector_min_score][: policy.max_visible_tools]
        fallback = False
        if not selected:
            # Conservative recall fallback: only already-policy-approved tools.
            # We do not resurrect write/execute/unknown tools rejected above.
            selected = ranked[: min(policy.safe_fallback_count, policy.max_visible_tools)]
            fallback = True

        return ToolSelection(
            query=query,
            selected_names=tuple(t.name for t in selected),
            rejected_by_policy=tuple(sorted(rejected)),
            scores=scores,
            fallback_used=fallback,
        )
