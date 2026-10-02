"""Transparent query-to-modality routing for Phase 3."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass

from extensions.omnirag.retrieval.query_features import QueryFeatures, extract_query_features


def _flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class ModalityDecision:
    route: str
    use_visual: bool
    text_weight: float
    visual_weight: float
    rrf_k: int
    agreement_bonus: float
    visual_top_k: int
    confidence: float
    rationale: tuple[str, ...]

    def as_dict(self) -> dict:
        return asdict(self)


class ModalityRouterV1:
    """Deterministic first routing policy.

    Score spaces from a sparse/dense text retriever and a vision encoder are not
    directly comparable, so the downstream fusion uses weighted RRF. These
    weights control rank contribution rather than raw cosine values.
    """

    name = "modality_router_v1"

    def decide(self, query: str | QueryFeatures) -> ModalityDecision:
        f = query if isinstance(query, QueryFeatures) else extract_query_features(query)
        reasons: list[str] = []
        always_on = _flag("OMNIRAG_VISUAL_ALWAYS_ON", False)

        if f.visual_signal:
            route = "visual_explicit"
            use_visual = True
            text_weight, visual_weight = 0.38, 0.62
            top_k, confidence = 16, 0.94
            reasons.append("query explicitly references a figure/image/chart/table/topology")
        elif f.contains_identifier or f.lexical_signal or f.contains_quoted_phrase:
            route = "text_lexical"
            use_visual = always_on
            text_weight, visual_weight = (0.90, 0.10) if use_visual else (1.0, 0.0)
            top_k, confidence = 8, 0.90
            reasons.append("exact identifier or quoted lexical signal favors text retrieval")
        elif f.contains_cjk and f.semantic_signal:
            route = "semantic_crosslingual"
            use_visual = always_on
            text_weight, visual_weight = (0.78, 0.22) if use_visual else (1.0, 0.0)
            top_k, confidence = 12, 0.78
            reasons.append("cross-lingual semantic query primarily needs dense text retrieval")
        elif f.semantic_signal or f.token_estimate >= 11:
            route = "semantic_text"
            use_visual = always_on
            text_weight, visual_weight = (0.80, 0.20) if use_visual else (1.0, 0.0)
            top_k, confidence = 12, 0.72
            reasons.append("semantic query has no explicit visual evidence request")
        else:
            route = "balanced_text"
            use_visual = always_on
            text_weight, visual_weight = (0.82, 0.18) if use_visual else (1.0, 0.0)
            top_k, confidence = 10, 0.62
            reasons.append("no explicit visual signal; preserve text-first behavior")

        # weighted RRF is stable around k=60; keep an env override for ablation.
        rrf_k = max(1, int(os.getenv("OMNIRAG_MULTIMODAL_RRF_K", "60")))
        agreement_bonus = max(0.0, float(os.getenv("OMNIRAG_MODAL_AGREEMENT_BONUS", "0.35")))
        return ModalityDecision(
            route=route,
            use_visual=use_visual,
            text_weight=text_weight,
            visual_weight=visual_weight,
            rrf_k=rrf_k,
            agreement_bonus=agreement_bonus,
            visual_top_k=top_k,
            confidence=confidence,
            rationale=tuple(reasons),
        )
