"""Feature-flagged runtime bridge between RAGFlow chunks and visual retrieval."""

from __future__ import annotations

import asyncio
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from .fusion import fuse_text_and_visual
from .router import ModalityRouterV1
from .visual_encoder import encoder_from_env
from .visual_index import JsonlVisualIndex


def _flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class MultimodalRuntimeMeta:
    enabled: bool
    route: str
    used_visual: bool
    visual_hits: int
    fused_chunks: int
    reason: str

    def as_dict(self) -> dict:
        return asdict(self)


def _run_fusion(question: str, kbinfos: dict, kb_ids: list[str], doc_ids: list[str] | None, top_n: int) -> tuple[dict, MultimodalRuntimeMeta]:
    decision = ModalityRouterV1().decide(question)
    if not decision.use_visual:
        return kbinfos, MultimodalRuntimeMeta(True, decision.route, False, 0, len(kbinfos.get("chunks", [])), "router kept text-only retrieval")

    index_path = Path(os.getenv("OMNIRAG_VISUAL_INDEX", "artifacts/omnirag/visual_index.jsonl"))
    if not index_path.exists():
        return kbinfos, MultimodalRuntimeMeta(True, decision.route, False, 0, len(kbinfos.get("chunks", [])), f"visual index missing: {index_path}")

    encoder = encoder_from_env()
    qvec = encoder.encode_texts([question])[0]
    index = JsonlVisualIndex(index_path)
    hits = index.search(
        qvec,
        top_k=decision.visual_top_k,
        dataset_ids=set(kb_ids or []) or None,
        document_ids=set(doc_ids or []) or None,
    )
    fused = fuse_text_and_visual(kbinfos.get("chunks", []), hits, decision, top_n=top_n)
    out = dict(kbinfos)
    out["chunks"] = [item.chunk for item in fused]
    out["total"] = max(int(out.get("total", 0) or 0), len(out["chunks"]))

    # Preserve upstream document aggregations and add any document introduced
    # only by visual retrieval so citations/document summaries remain coherent.
    doc_aggs = list(out.get("doc_aggs") or [])
    known_docs = {str(row.get("doc_id") or "") for row in doc_aggs}
    for chunk in out["chunks"]:
        doc_id = str(chunk.get("doc_id") or "")
        if not doc_id or doc_id in known_docs:
            continue
        doc_aggs.append({
            "doc_name": chunk.get("docnm_kwd", ""),
            "doc_id": doc_id,
            "count": 1,
        })
        known_docs.add(doc_id)
    out["doc_aggs"] = doc_aggs
    out["omnirag_multimodal"] = {
        "router": decision.as_dict(),
        "visual_hits": len(hits),
        "visual_hit_chunk_ids": [hit.record.chunk_id for hit in hits],
        "visual_hit_image_ids": [hit.record.image_id for hit in hits],
    }
    return out, MultimodalRuntimeMeta(True, decision.route, True, len(hits), len(fused), "weighted RRF fusion applied")


async def maybe_fuse_multimodal(
    question: str,
    kbinfos: dict,
    kb_ids: list[str],
    doc_ids: list[str] | None,
    top_n: int,
) -> tuple[dict, dict]:
    if not _flag("OMNIRAG_MULTIMODAL_RETRIEVAL", False):
        meta = MultimodalRuntimeMeta(False, "disabled", False, 0, len(kbinfos.get("chunks", [])), "OMNIRAG_MULTIMODAL_RETRIEVAL is disabled")
        return kbinfos, meta.as_dict()

    out, meta = await asyncio.to_thread(_run_fusion, question, kbinfos, kb_ids, doc_ids, top_n)
    return out, meta.as_dict()
