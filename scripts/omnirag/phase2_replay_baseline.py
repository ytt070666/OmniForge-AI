#!/usr/bin/env python3
"""Replay a completed Phase-1 weight sweep to estimate adaptive-policy headroom.

No live RAGFlow call is made. The script chooses, for each query, the already
observed fixed-weight row nearest to the heuristic policy's final weight and
compares it with the best fixed setting and an oracle upper bound.
"""

from __future__ import annotations

import argparse
import json
import sys
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from extensions.omnirag.retrieval.adaptive_policy import HeuristicPolicyV1
from extensions.omnirag.retrieval.query_features import extract_query_features
BENCH = ROOT / "benchmarks" / "omnirag" / "phase1"


def load(path: Path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def norm(v):
    return Path(str(v or "")).name.lower()


def rank(row):
    expected = norm(row.get("expected_document"))
    markers = [str(x).lower() for x in row.get("expected_markers", [])]
    for i, chunk in enumerate(row.get("chunks", []), 1):
        actual = norm(chunk.get("document_keyword") or chunk.get("docnm_kwd"))
        content = str(chunk.get("content") or chunk.get("content_with_weight") or "").lower()
        if actual == expected or (actual and expected and (actual in expected or expected in actual)):
            return i
        if markers and any(m in content for m in markers):
            return i
    return None


def rr(r):
    return 0.0 if r is None else 1.0 / r


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--results-dir", type=Path)
    args = p.parse_args()
    results_dir = args.results_dir
    if results_dir is None:
        latest = BENCH / "results" / "LATEST"
        if not latest.exists():
            p.error("Phase-1 baseline does not exist yet. This replay is intentionally deferred until after local baseline collection.")
        results_dir = BENCH / "results" / latest.read_text(encoding="utf-8").strip()

    rows = load(results_dir / "retrieval_results.jsonl")
    by_q = defaultdict(list)
    for row in rows:
        by_q[row["query_id"]].append(row)

    policy = HeuristicPolicyV1()
    adaptive_rr, oracle_rr = [], []
    fixed = defaultdict(list)
    detail = []
    for qid, group in sorted(by_q.items()):
        q = group[0]
        decision = policy.decide(extract_query_features(q["question"]))
        selected = min(group, key=lambda r: abs(float(r["vector_similarity_weight"]) - decision.final_vector_weight))
        selected_rank = rank(selected)
        adaptive_rr.append(rr(selected_rank))
        best_row = max(group, key=lambda r: rr(rank(r)))
        oracle_rr.append(rr(rank(best_row)))
        for row in group:
            fixed[float(row["vector_similarity_weight"])].append(rr(rank(row)))
        detail.append({
            "id": qid,
            "route": decision.route,
            "target_weight": decision.final_vector_weight,
            "selected_observed_weight": float(selected["vector_similarity_weight"]),
            "selected_rank": selected_rank,
            "oracle_weight": float(best_row["vector_similarity_weight"]),
            "oracle_rank": rank(best_row),
        })

    mean = lambda xs: sum(xs) / len(xs) if xs else 0.0
    summary = {
        "adaptive_replay_mrr": mean(adaptive_rr),
        "oracle_mrr": mean(oracle_rr),
        "fixed_weight_mrr": {str(k): mean(v) for k, v in sorted(fixed.items())},
        "details": detail,
        "warning": "Replay evaluates only the final fusion weight using previously observed fixed-weight results. Candidate-stage adaptation requires a live Phase-2 run."
    }
    out = results_dir / "PHASE2_OFFLINE_REPLAY.json"
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
