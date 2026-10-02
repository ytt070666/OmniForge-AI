#!/usr/bin/env python3
"""Preview the adaptive policy over the Phase-1 benchmark without RAGFlow."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from extensions.omnirag.retrieval.adaptive_policy import HeuristicPolicyV1
from extensions.omnirag.retrieval.query_features import extract_query_features
DEFAULT_QUERIES = ROOT / "benchmarks" / "omnirag" / "phase1" / "queries.jsonl"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--queries", type=Path, default=DEFAULT_QUERIES)
    p.add_argument("--out", type=Path, default=ROOT / "artifacts" / "omnirag" / "prelocal" / "phase2_policy_preview.jsonl")
    args = p.parse_args()

    policy = HeuristicPolicyV1()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    routes = Counter()
    by_category = defaultdict(Counter)
    rows = []
    for raw in args.queries.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        q = json.loads(raw)
        features = extract_query_features(q["question"])
        decision = policy.decide(features)
        routes[decision.route] += 1
        by_category[q["category"]][decision.route] += 1
        rows.append({
            "id": q["id"],
            "benchmark_category": q["category"],
            "question": q["question"],
            "features": features.as_dict(),
            "decision": decision.as_dict(),
        })

    with args.out.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary = {
        "queries": len(rows),
        "routes": dict(routes),
        "by_benchmark_category": {k: dict(v) for k, v in sorted(by_category.items())},
        "output": str(args.out),
    }
    summary_path = args.out.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
