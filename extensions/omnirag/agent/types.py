"""Shared contracts for OmniRAG Phase-4 agent governance.

The extension deliberately keeps these contracts independent from RAGFlow's
runtime classes so policy logic can be unit-tested without MySQL, Redis, a model
provider, or a live document engine.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class AgentAction(StrEnum):
    ACCEPT = "accept"
    RETRIEVE_MORE = "retrieve_more"
    ABSTAIN = "abstain"


class PlanningMode(StrEnum):
    DIRECT = "direct"
    RESEARCH = "research"
    VISUAL_RESEARCH = "visual_research"
    EXACT_LOOKUP = "exact_lookup"


@dataclass(frozen=True)
class MemoryItem:
    memory_id: str
    message_id: str
    memory_type: str
    content: str
    valid_at: str = ""
    source_rank: int = 0
    rank_score: float = 0.0
    lexical_overlap: float = 0.0
    recency_score: float = 0.0
    final_score: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PlanningDecision:
    mode: PlanningMode
    use_long_term_memory: bool
    allowed_memory_types: tuple[str, ...]
    retry_budget: int
    strict_evidence: bool
    requires_visual: bool
    rationale: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["mode"] = self.mode.value
        return d


@dataclass(frozen=True)
class CriticDecision:
    action: AgentAction
    reason: str
    confidence: float
    missing_targets: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()
    retry_query: str = ""

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["action"] = self.action.value
        return d


@dataclass(frozen=True)
class AttemptRecord:
    attempt: int
    query: str
    answer: str
    verification: dict[str, Any]
    rag_verdict: dict[str, Any]
    critic: CriticDecision
    retrieved_chunk_ids: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["critic"] = self.critic.as_dict()
        return d


@dataclass
class AgentTrace:
    original_query: str
    plan: PlanningDecision
    memory_items: list[MemoryItem] = field(default_factory=list)
    attempts: list[AttemptRecord] = field(default_factory=list)
    terminal_action: AgentAction | None = None
    termination_reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "original_query": self.original_query,
            "plan": self.plan.as_dict(),
            "memory_items": [m.as_dict() for m in self.memory_items],
            "attempts": [a.as_dict() for a in self.attempts],
            "terminal_action": self.terminal_action.value if self.terminal_action else None,
            "termination_reason": self.termination_reason,
        }


@dataclass(frozen=True)
class AgentRunResult:
    answer: str
    action: AgentAction
    trace: AgentTrace
    final_query: str
    reference: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "action": self.action.value,
            "trace": self.trace.as_dict(),
            "final_query": self.final_query,
            "reference": self.reference,
            "metadata": self.metadata,
        }
