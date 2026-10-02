"""Schemas and validation for Phase-6 advisory router data.

The trained model is deliberately advisory. Its output can tune retrieval and
suggest tool intent, but it is never an authorization source. Phase-5 hard
policy and Phase-3 evidence verification remain authoritative.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

QUERY_CLASSES = (
    "lexical_precision",
    "semantic",
    "hybrid",
    "crosslingual",
    "visual",
    "tool",
)
RETRIEVAL_PROFILES = ("sparse_heavy", "balanced", "dense_heavy")
TOOL_INTENTS = (
    "none",
    "knowledge_search",
    "weather",
    "device_lookup",
    "runbook_search",
    "availability_calc",
)
EVIDENCE_STRICTNESS = ("normal", "high")
REQUIRED_OUTPUT_KEYS = (
    "query_class",
    "retrieval_profile",
    "needs_visual",
    "needs_tools",
    "tool_intent",
    "evidence_strictness",
)

SYSTEM_PROMPT = (
    "You are the OmniRAG advisory control router. Classify the user query and "
    "return exactly one JSON object with keys query_class, retrieval_profile, "
    "needs_visual, needs_tools, tool_intent, evidence_strictness. Do not add "
    "authorization fields, executable code, prose, or markdown. Your output is "
    "advisory only; downstream deterministic safety policy remains authoritative."
)


class RouterSchemaError(ValueError):
    pass


def canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def validate_router_output(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RouterSchemaError("router output must be an object")
    if set(value) != set(REQUIRED_OUTPUT_KEYS):
        missing = sorted(set(REQUIRED_OUTPUT_KEYS) - set(value))
        extra = sorted(set(value) - set(REQUIRED_OUTPUT_KEYS))
        raise RouterSchemaError(f"router output keys mismatch; missing={missing}, extra={extra}")
    if value["query_class"] not in QUERY_CLASSES:
        raise RouterSchemaError("invalid query_class")
    if value["retrieval_profile"] not in RETRIEVAL_PROFILES:
        raise RouterSchemaError("invalid retrieval_profile")
    if not isinstance(value["needs_visual"], bool):
        raise RouterSchemaError("needs_visual must be boolean")
    if not isinstance(value["needs_tools"], bool):
        raise RouterSchemaError("needs_tools must be boolean")
    if value["tool_intent"] not in TOOL_INTENTS:
        raise RouterSchemaError("invalid tool_intent")
    if value["evidence_strictness"] not in EVIDENCE_STRICTNESS:
        raise RouterSchemaError("invalid evidence_strictness")
    if value["query_class"] == "visual" and not value["needs_visual"]:
        raise RouterSchemaError("visual queries must set needs_visual=true")
    if value["query_class"] == "tool" and not value["needs_tools"]:
        raise RouterSchemaError("tool queries must set needs_tools=true")
    if value["needs_tools"] and value["tool_intent"] == "none":
        raise RouterSchemaError("tool query must declare a non-none advisory tool_intent")
    if not value["needs_tools"] and value["tool_intent"] != "none":
        raise RouterSchemaError("non-tool query cannot carry tool_intent")
    return value


def make_completion(
    *,
    query_class: str,
    retrieval_profile: str,
    needs_visual: bool = False,
    needs_tools: bool = False,
    tool_intent: str = "none",
    evidence_strictness: str = "normal",
) -> str:
    value = {
        "query_class": query_class,
        "retrieval_profile": retrieval_profile,
        "needs_visual": needs_visual,
        "needs_tools": needs_tools,
        "tool_intent": tool_intent,
        "evidence_strictness": evidence_strictness,
    }
    validate_router_output(value)
    return canonical_json(value)


@dataclass(frozen=True)
class RouterExample:
    id: str
    family_id: str
    source_type: str
    query: str
    completion: str
    language: str = "en"
    source_ref: str = "phase6_template"

    def as_record(self) -> dict[str, Any]:
        validate_router_output(json.loads(self.completion))
        return {
            "id": self.id,
            "family_id": self.family_id,
            "source_type": self.source_type,
            "source_ref": self.source_ref,
            "language": self.language,
            "prompt": f"{SYSTEM_PROMPT}\n\nUser query:\n{self.query}",
            "completion": self.completion,
            "query": self.query,
        }
