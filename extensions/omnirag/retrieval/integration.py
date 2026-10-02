"""Runtime integration boundary for adaptive retrieval.

The module has no RAGFlow imports, so it can be unit tested without starting the
full stack. RAGFlow core code calls this boundary only after the Phase-1 patch is
applied.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, asdict

from .adaptive_policy import HeuristicPolicyV1
from .query_features import extract_query_features


def _flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class AdaptiveRetrievalDecision:
    enabled: bool
    policy: str
    route: str
    candidate_vector_weight: float
    final_vector_weight: float
    knn_top_k: int
    knn_num_candidates: int
    requires_vision: bool
    confidence: float
    rationale: tuple[str, ...]
    original_vector_weight: float

    def as_dict(self) -> dict:
        return asdict(self)


def maybe_adapt_retrieval(
    question: str,
    vector_similarity_weight: float,
    knn_top_k: int,
    knn_num_candidates: int,
) -> AdaptiveRetrievalDecision:
    enabled = _flag("OMNIRAG_ADAPTIVE_RETRIEVAL", False)
    original = float(vector_similarity_weight)
    if not enabled:
        return AdaptiveRetrievalDecision(
            enabled=False,
            policy="disabled",
            route="upstream",
            candidate_vector_weight=0.999,
            final_vector_weight=original,
            knn_top_k=int(knn_top_k),
            knn_num_candidates=int(knn_num_candidates),
            requires_vision=False,
            confidence=1.0,
            rationale=("OmniRAG adaptive retrieval is disabled; preserve upstream behavior",),
            original_vector_weight=original,
        )

    policy_name = os.getenv("OMNIRAG_ADAPTIVE_POLICY", "heuristic_v1").strip()
    if policy_name != "heuristic_v1":
        raise ValueError(f"Unsupported OMNIRAG_ADAPTIVE_POLICY={policy_name!r}")

    policy = HeuristicPolicyV1()
    pd = policy.decide(extract_query_features(question), knn_top_k, knn_num_candidates)

    candidate_enabled = _flag("OMNIRAG_ADAPTIVE_CANDIDATE", True)
    final_enabled = _flag("OMNIRAG_ADAPTIVE_FINAL", True)
    candidate_weight = pd.candidate_vector_weight if candidate_enabled else 0.999
    final_weight = pd.final_vector_weight if final_enabled else original

    return AdaptiveRetrievalDecision(
        enabled=True,
        policy=policy.name,
        route=pd.route,
        candidate_vector_weight=candidate_weight,
        final_vector_weight=final_weight,
        knn_top_k=pd.knn_top_k,
        knn_num_candidates=pd.knn_num_candidates,
        requires_vision=pd.requires_vision,
        confidence=pd.confidence,
        rationale=pd.rationale,
        original_vector_weight=original,
    )
