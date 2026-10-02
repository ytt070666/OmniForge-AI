#!/usr/bin/env python3
"""Collect a live adaptive-retrieval run after the Phase-2 patch is applied."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.omnirag.phase1_collect_baseline import RagflowClient, compact_chunk, load_queries, ping

BENCH = ROOT / "benchmarks" / "omnirag" / "phase1"
QUERIES = BENCH / "queries.jsonl"
PHASE2_RESULTS = ROOT / "benchmarks" / "omnirag" / "phase2" / "results"


def find_baseline_manifest(path: Path | None) -> tuple[Path, dict]:
    if path is None:
        latest = BENCH / "results" / "LATEST"
        if not latest.exists():
            raise SystemExit("No Phase-1 LATEST marker exists. Collect the baseline first.")
        path = BENCH / "results" / latest.read_text(encoding="utf-8").strip() / "run_manifest.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("baseline", {}).get("algorithm_modified") is not False:
        raise SystemExit("Selected manifest is not an untouched Phase-1 baseline.")
    return path, data


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--api-root", default=os.getenv("RAGFLOW_API_ROOT", "http://127.0.0.1:9380/api/v1"))
    p.add_argument("--api-key", default=os.getenv("RAGFLOW_API_KEY"))
    p.add_argument("--baseline-manifest", type=Path)
    p.add_argument("--dataset-id")
    p.add_argument("--run-label", default="adaptive")
    p.add_argument("--page-size", type=int, default=10)
    p.add_argument("--caller-weight", type=float, default=0.3, help="upstream caller value; adaptive final policy overrides it when enabled")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    manifest_path, baseline = find_baseline_manifest(args.baseline_manifest)
    dataset_id = args.dataset_id or (baseline.get("dataset") or {}).get("id")
    if not dataset_id:
        p.error("dataset id is missing from both CLI and baseline manifest")
    queries = load_queries(QUERIES)

    if args.dry_run:
        print(json.dumps({
            "baseline_manifest": str(manifest_path),
            "dataset_id": dataset_id,
            "queries": len(queries),
            "run_label": args.run_label,
            "caller_weight": args.caller_weight,
        }, indent=2, ensure_ascii=False))
        return 0
    if not args.api_key:
        p.error("RAGFLOW_API_KEY is required")

    client = RagflowClient(args.api_root, args.api_key)
    system = ping(client)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + args.run_label
    outdir = PHASE2_RESULTS / run_id
    outdir.mkdir(parents=True, exist_ok=True)
    outfile = outdir / "retrieval_results.jsonl"

    with outfile.open("w", encoding="utf-8") as sink:
        for i, q in enumerate(queries, 1):
            body = {
                "dataset_ids": [dataset_id],
                "question": q["question"],
                "page": 1,
                "page_size": args.page_size,
                "similarity_threshold": 0.0,
                "vector_similarity_weight": args.caller_weight,
                "knn_top_k": 128,
                "knn_num_candidates": 256,
                "rerank_candidates_count": 64,
                "highlight": False,
                "include_knowledge_compilation": False,
            }
            started = time.perf_counter()
            payload = client.post("retrieval", json=body, timeout=180)
            latency_ms = (time.perf_counter() - started) * 1000
            data = payload.get("data") or {}
            decision = data.get("omnirag_retrieval")
            if not isinstance(decision, dict) or not decision.get("enabled"):
                raise RuntimeError(
                    "Server response has no enabled omnirag_retrieval metadata. "
                    "Apply the Phase-2 patch and set OMNIRAG_ADAPTIVE_RETRIEVAL=1 before this run."
                )
            chunks = [compact_chunk(c, rank + 1) for rank, c in enumerate(data.get("chunks") or [])]
            row = {
                "query_id": q["id"],
                "category": q["category"],
                "question": q["question"],
                "expected_document": q["expected_document"],
                "expected_markers": q.get("expected_markers", []),
                "caller_vector_similarity_weight": args.caller_weight,
                "adaptive": decision,
                "latency_ms": round(latency_ms, 3),
                "retrieved_total": data.get("total", 0),
                "chunks": chunks,
            }
            sink.write(json.dumps(row, ensure_ascii=False) + "\n")
            sink.flush()
            print(
                f"[{i:02d}/{len(queries):02d}] {q['id']} route={decision.get('route')} "
                f"wc={decision.get('candidate_vector_weight')} wf={decision.get('final_vector_weight')} {latency_ms:.1f}ms",
                flush=True,
            )

    run_manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "phase": 2,
        "run_label": args.run_label,
        "baseline_manifest": str(manifest_path),
        "dataset_id": dataset_id,
        "caller_weight": args.caller_weight,
        "system": system,
        "results": str(outfile.relative_to(ROOT)),
    }
    (outdir / "run_manifest.json").write_text(json.dumps(run_manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    PHASE2_RESULTS.mkdir(parents=True, exist_ok=True)
    (PHASE2_RESULTS / "LATEST").write_text(run_id + "\n", encoding="utf-8")
    print(f"PASS: adaptive retrieval collected under {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
