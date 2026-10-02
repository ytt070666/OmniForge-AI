#!/usr/bin/env python3
"""Evaluate Phase-3 visual retrieval results with Recall@K and MRR."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "benchmarks" / "omnirag" / "phase3"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=BENCH / "results" / "visual_retrieval.jsonl")
    ap.add_argument("--output", type=Path, default=BENCH / "results" / "visual_metrics.json")
    args = ap.parse_args()
    rows = [json.loads(x) for x in args.input.read_text(encoding="utf-8").splitlines() if x.strip()]
    acc = defaultdict(lambda: {"n":0,"r1":0,"r3":0,"r5":0,"rr":0.0})
    for row in rows:
        expected = set(row.get("expected_chunks") or [row.get("expected_chunk")])
        expected.discard(None)
        ranked = [x["record"]["chunk_id"] if "record" in x else x.get("chunk_id") for x in row.get("fused", [])]
        # FusedCandidate serialization nests chunk, but chunk_id is top-level.
        ranked = [x.get("chunk_id") for x in row.get("fused", [])]
        ranks = [i+1 for i, cid in enumerate(ranked) if cid in expected]
        first = min(ranks) if ranks else None
        for key in ("all", row.get("category", "unknown")):
            a = acc[key]; a["n"] += 1
            a["r1"] += int(first is not None and first <= 1)
            a["r3"] += int(first is not None and first <= 3)
            a["r5"] += int(first is not None and first <= 5)
            a["rr"] += 0.0 if first is None else 1.0/first
    report = {}
    for key, a in sorted(acc.items()):
        n = max(1, a["n"])
        report[key] = {"count":a["n"],"Recall@1":a["r1"]/n,"Recall@3":a["r3"]/n,"Recall@5":a["r5"]/n,"MRR":a["rr"]/n}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
