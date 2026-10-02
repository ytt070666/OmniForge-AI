"""Post-generation evidence verification bridge.

Phase 3 reports confidence and conflicts but does not silently rewrite answers.
A later Agent/Critic phase can consume ``decision=retrieve_more`` to trigger an
explicit second retrieval/generation loop.
"""

from __future__ import annotations

import os

from .evidence import EvidenceItem
from .evidence_graph import verify_claims


def _flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _chunk_to_evidence(chunk: dict, index: int) -> EvidenceItem:
    modality = chunk.get("doc_type_kwd") or ("image" if chunk.get("image_id") else "text")
    return EvidenceItem(
        evidence_id=str(chunk.get("chunk_id") or chunk.get("id") or index),
        source=str(chunk.get("docnm_kwd") or chunk.get("document_keyword") or ""),
        content=str(chunk.get("content_with_weight") or chunk.get("content_ltks") or chunk.get("content") or ""),
        modality=str(modality),
        retrieval_score=float(chunk.get("similarity", 0.0) or 0.0),
    )


def maybe_verify_answer(answer: str, chunks: list[dict]) -> dict:
    if not _flag("OMNIRAG_EVIDENCE_VERIFIER", False):
        return {"enabled": False, "decision": "disabled"}
    evidence = [_chunk_to_evidence(chunk, i) for i, chunk in enumerate(chunks)]
    report = verify_claims(
        answer,
        evidence,
        support_threshold=float(os.getenv("OMNIRAG_EVIDENCE_SUPPORT_THRESHOLD", "0.42")),
        pass_threshold=float(os.getenv("OMNIRAG_EVIDENCE_PASS_THRESHOLD", "0.62")),
        abstain_threshold=float(os.getenv("OMNIRAG_EVIDENCE_ABSTAIN_THRESHOLD", "0.34")),
    )
    out = report.as_dict()
    out["enabled"] = True
    out["method"] = "deterministic_v1"
    return out
