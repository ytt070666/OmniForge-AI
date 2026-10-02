#!/usr/bin/env python3
"""Collect visual retrieval + fusion results for the Phase-3 benchmark."""

from __future__ import annotations

import argparse
import sys
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
BENCH = ROOT / "benchmarks" / "omnirag" / "phase3"

from extensions.omnirag.multimodal.fusion import fuse_text_and_visual
from extensions.omnirag.multimodal.router import ModalityRouterV1
from extensions.omnirag.multimodal.visual_encoder import HashEncoderForTests, Siglip2Encoder
from extensions.omnirag.multimodal.visual_index import JsonlVisualIndex


def encoder(name: str):
    if name == "hash":
        print("WARNING: hash encoder is plumbing-only; do not report these values as research metrics")
        return HashEncoderForTests()
    return Siglip2Encoder()


def load_jsonl(path: Path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--index", type=Path, default=ROOT / "artifacts" / "omnirag" / "visual_index.jsonl")
    ap.add_argument("--encoder", choices=["siglip2", "hash"], default=os.getenv("OMNIRAG_VISUAL_ENCODER", "siglip2"))
    ap.add_argument("--output", type=Path, default=BENCH / "results" / "visual_retrieval.jsonl")
    ap.add_argument("--top-k", type=int, default=6)
    args = ap.parse_args()
    enc = encoder(args.encoder)
    idx = JsonlVisualIndex(args.index)
    queries = load_jsonl(BENCH / "queries.jsonl")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as sink:
        for q in queries:
            decision = ModalityRouterV1().decide(q["question"])
            qv = enc.encode_texts([q["question"]])[0]
            hits = idx.search(qv, top_k=max(args.top_k, decision.visual_top_k), dataset_ids={"phase3-mm"})
            # Pure visual benchmark: empty text list. Full RAGFlow ablation will
            # supply real text chunks after Phase-3 patch activation.
            fused = fuse_text_and_visual([], hits, decision, top_n=args.top_k)
            row = dict(q)
            row["router"] = decision.as_dict()
            row["hits"] = [x.as_dict() for x in hits[:args.top_k]]
            row["fused"] = [x.as_dict() for x in fused]
            sink.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(q["id"], "->", [x.record.chunk_id for x in hits[:3]])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
