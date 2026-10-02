"""Deterministic planning policy that augments, rather than replaces, RAGFlow.

RAGFlow 0.27.2 already contains a capable agentic-RAG planner, sufficient-context
review, query rewriting, and bounded follow-up search. Phase 4 therefore does
not add a competing LLM planner. This policy only decides governance settings
that RAGFlow's existing planner should operate under: memory usage, retry budget,
visual requirements, and evidence strictness.
"""

from __future__ import annotations

from .types import PlanningDecision, PlanningMode
from extensions.omnirag.retrieval.query_features import extract_query_features


class PlanningPolicyV1:
    name = "planning_policy_v1"

    def decide(self, query: str) -> PlanningDecision:
        f = extract_query_features(query)
        reasons: list[str] = []

        if f.visual_signal:
            mode = PlanningMode.VISUAL_RESEARCH
            retry_budget = 2
            strict = True
            reasons.append("visual signal requires multimodal evidence and cross-modal verification")
        elif f.contains_identifier or f.lexical_signal or f.contains_quoted_phrase:
            mode = PlanningMode.EXACT_LOOKUP
            retry_budget = 1
            strict = True
            reasons.append("exact identifiers favor a short, precision-first research plan")
        elif f.semantic_signal or f.token_estimate >= 11 or f.contains_cjk:
            mode = PlanningMode.RESEARCH
            retry_budget = 2
            strict = True
            reasons.append("semantic or multi-part query benefits from iterative evidence gathering")
        else:
            mode = PlanningMode.DIRECT
            retry_budget = 1
            strict = True
            reasons.append("simple query keeps the smallest bounded research budget")

        # Long-term memory is planning context only. Semantic memory is excluded
        # by default because remembered facts are not primary evidence and can be
        # stale. Procedural and episodic memories may guide strategy without being
        # cited as factual support.
        return PlanningDecision(
            mode=mode,
            use_long_term_memory=True,
            allowed_memory_types=("procedural", "episodic"),
            retry_budget=retry_budget,
            strict_evidence=strict,
            requires_visual=f.visual_signal,
            rationale=tuple(reasons),
        )
