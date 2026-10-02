"""Query-adaptive weighted reciprocal-rank fusion for text + visual evidence."""

from __future__ import annotations

from collections import OrderedDict
from typing import Iterable

from .router import ModalityDecision
from .types import FusedCandidate, VisualHit


def _rrf(weight: float, rank: int | None, k: int) -> float:
    if rank is None or weight <= 0:
        return 0.0
    return float(weight) / float(k + rank)


def fuse_text_and_visual(
    text_chunks: list[dict],
    visual_hits: Iterable[VisualHit],
    decision: ModalityDecision,
    top_n: int,
) -> list[FusedCandidate]:
    """Fuse candidates without comparing incompatible raw score scales.

    RAGFlow text similarity and vision-encoder cosine similarity can have very
    different calibration. Weighted RRF uses ranks, while an agreement bonus
    rewards a chunk independently surfaced by both modalities.
    """

    rows: "OrderedDict[str, dict]" = OrderedDict()

    for rank, chunk in enumerate(text_chunks, start=1):
        cid = str(chunk.get("chunk_id") or chunk.get("id") or "")
        if not cid:
            continue
        rows[cid] = {
            "chunk": dict(chunk),
            "text_rank": rank,
            "text_score": float(chunk.get("similarity", 0.0)),
            "visual_rank": None,
            "visual_score": None,
        }

    for hit in visual_hits:
        rec = hit.record
        cid = str(rec.chunk_id)
        if cid not in rows:
            rows[cid] = {
                "chunk": {
                    "chunk_id": cid,
                    "content_ltks": rec.content,
                    "content_with_weight": rec.content,
                    "doc_id": rec.document_id,
                    "docnm_kwd": rec.document_name,
                    "kb_id": rec.dataset_id,
                    "image_id": rec.image_id,
                    "doc_type_kwd": rec.doc_type,
                    "important_kwd": [],
                    "tag_kwd": [],
                    "positions": rec.metadata.get("positions", []),
                    "term_similarity": 0.0,
                    "vector_similarity": 0.0,
                },
                "text_rank": None,
                "text_score": None,
                "visual_rank": int(hit.rank),
                "visual_score": float(hit.score),
            }
        else:
            rows[cid]["visual_rank"] = int(hit.rank)
            rows[cid]["visual_score"] = float(hit.score)
            # Prefer a real image id from the visual sidecar when upstream text
            # retrieval omitted it.
            if not rows[cid]["chunk"].get("image_id"):
                rows[cid]["chunk"]["image_id"] = rec.image_id
            if not rows[cid]["chunk"].get("doc_type_kwd"):
                rows[cid]["chunk"]["doc_type_kwd"] = rec.doc_type

    fused: list[FusedCandidate] = []
    for cid, row in rows.items():
        t_rank = row["text_rank"]
        v_rank = row["visual_rank"]
        score = _rrf(decision.text_weight, t_rank, decision.rrf_k) + _rrf(decision.visual_weight, v_rank, decision.rrf_k)
        agreement = t_rank is not None and v_rank is not None
        if agreement:
            # Scale the bonus by the weaker modality's RRF contribution so it
            # cannot dominate the base score.
            weaker = min(
                _rrf(decision.text_weight, t_rank, decision.rrf_k),
                _rrf(decision.visual_weight, v_rank, decision.rrf_k),
            )
            score += decision.agreement_bonus * weaker

        chunk = row["chunk"]
        chunk["similarity"] = float(score)
        chunk["omnirag_multimodal"] = {
            "route": decision.route,
            "text_rank": t_rank,
            "visual_rank": v_rank,
            "text_score": row["text_score"],
            "visual_score": row["visual_score"],
            "fused_score": float(score),
            "agreement": agreement,
        }
        fused.append(
            FusedCandidate(
                chunk_id=cid,
                fused_score=float(score),
                text_rank=t_rank,
                visual_rank=v_rank,
                text_score=row["text_score"],
                visual_score=row["visual_score"],
                agreement=agreement,
                chunk=chunk,
            )
        )

    fused.sort(key=lambda x: (-x.fused_score, x.chunk_id))
    return fused[: max(0, int(top_n))]
