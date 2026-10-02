"""Runtime policy for tool visibility and execution."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from .types import ToolDescriptor, ToolRisk


def _truthy(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _bounded_int(name: str, default: int, low: int, high: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except Exception:
        value = default
    return max(low, min(high, value))


@dataclass(frozen=True)
class ToolPolicy:
    allowed_risks: frozenset[ToolRisk] = field(default_factory=lambda: frozenset({ToolRisk.READ}))
    allow_destructive: bool = False
    allow_open_world: bool = False
    max_visible_tools: int = 6
    max_total_calls: int = 8
    max_calls_per_tool: int = 3
    selector_min_score: float = 0.05
    safe_fallback_count: int = 4

    def permits(self, tool: ToolDescriptor) -> tuple[bool, str]:
        if tool.risk not in self.allowed_risks:
            return False, f"risk={tool.risk.value} is not allowed"
        if tool.destructive is True and not self.allow_destructive:
            return False, "destructive tool is not allowed"
        if tool.open_world is True and not self.allow_open_world:
            return False, "open-world tool is not allowed"
        return True, "allowed"


def governance_enabled() -> bool:
    return _truthy("OMNIRAG_TOOL_GOVERNANCE", False)


def policy_from_env() -> ToolPolicy:
    raw = os.getenv("OMNIRAG_TOOL_ALLOWED_RISKS", "read")
    allowed: set[ToolRisk] = set()
    for value in raw.split(","):
        value = value.strip().lower()
        try:
            allowed.add(ToolRisk(value))
        except ValueError:
            continue
    if not allowed:
        allowed = {ToolRisk.READ}

    try:
        min_score = float(os.getenv("OMNIRAG_TOOL_SELECTOR_MIN_SCORE", "0.05"))
    except Exception:
        min_score = 0.05
    min_score = max(0.0, min(1.0, min_score))

    return ToolPolicy(
        allowed_risks=frozenset(allowed),
        allow_destructive=_truthy("OMNIRAG_TOOL_ALLOW_DESTRUCTIVE", False),
        allow_open_world=_truthy("OMNIRAG_TOOL_ALLOW_OPEN_WORLD", False),
        max_visible_tools=_bounded_int("OMNIRAG_TOOL_MAX_VISIBLE", 6, 1, 32),
        max_total_calls=_bounded_int("OMNIRAG_TOOL_MAX_CALLS", 8, 1, 64),
        max_calls_per_tool=_bounded_int("OMNIRAG_TOOL_MAX_CALLS_PER_TOOL", 3, 1, 16),
        selector_min_score=min_score,
        safe_fallback_count=_bounded_int("OMNIRAG_TOOL_SAFE_FALLBACK", 4, 0, 16),
    )
