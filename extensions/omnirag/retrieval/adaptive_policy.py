"""Transparent two-stage adaptive hybrid-retrieval policy."""

from __future__ import annotations

from dataclasses import dataclass, asdict

from .query_features import QueryFeatures


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


@dataclass(frozen=True)
class PolicyDecision:
    route: str
    candidate_vector_weight: float
    final_vector_weight: float
    knn_top_k: int
    knn_num_candidates: int
    requires_vision: bool
    confidence: float
    rationale: tuple[str, ...]

    def as_dict(self) -> dict:
        return asdict(self)


class HeuristicPolicyV1:
    """First reproducible policy used to test the adaptive-retrieval hypothesis.

    It separates candidate acquisition from final fusion:
    - candidate_vector_weight influences ES dense/sparse candidate fusion;
    - final_vector_weight influences the local final similarity fusion.

    The policy is intentionally small enough to explain in an interview and to
    ablate in a paper. It is not claimed to be globally optimal.
    """

    name = "heuristic_v1"

    def decide(self, f: QueryFeatures, base_top_k: int = 1024, base_num_candidates: int = 2048) -> PolicyDecision:
        reasons: list[str] = []

        if f.visual_signal:
            route = "visual_or_mixed"
            candidate = 0.78
            final = 0.72
            confidence = 0.90
            reasons.append("visual terms indicate that text-only lexical matching may be insufficient")
        elif f.contains_cjk:
            route = "crosslingual_semantic"
            candidate = 0.85
            final = 0.82
            confidence = 0.90
            reasons.append("CJK query against a potentially multilingual corpus benefits from dense semantics")
        elif f.contains_identifier or f.lexical_signal or f.contains_quoted_phrase:
            route = "lexical_precision"
            candidate = 0.35
            final = 0.22
            confidence = 0.88
            reasons.append("identifier/exact-match signals favor sparse lexical evidence")
        elif f.semantic_signal or f.token_estimate >= 11:
            route = "semantic"
            candidate = 0.72
            final = 0.70
            confidence = 0.78
            reasons.append("explanatory/paraphrased query favors dense semantic retrieval")
        else:
            route = "hybrid"
            candidate = 0.58
            final = 0.52
            confidence = 0.62
            reasons.append("no dominant signal; use balanced hybrid retrieval")

        # Candidate-pool policy: semantic/cross-lingual/visual routes get a wider
        # pool because relevant lexical overlap can be weak. Exact identifier
        # queries use a smaller pool to reduce downstream rerank cost.
        if route == "lexical_precision":
            top_k = min(base_top_k, 768)
            num_candidates = min(base_num_candidates, 1536)
        elif route in {"crosslingual_semantic", "visual_or_mixed"}:
            top_k = max(base_top_k, 1280)
            num_candidates = max(base_num_candidates, 2560)
        else:
            top_k = base_top_k
            num_candidates = base_num_candidates

        return PolicyDecision(
            route=route,
            candidate_vector_weight=clamp(candidate),
            final_vector_weight=clamp(final),
            knn_top_k=int(top_k),
            knn_num_candidates=int(num_candidates),
            requires_vision=(route == "visual_or_mixed"),
            confidence=confidence,
            rationale=tuple(reasons),
        )
