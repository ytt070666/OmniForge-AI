#!/usr/bin/env python3
"""Evaluate a Phase-2 adaptive run and compare it with the frozen baseline."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.omnirag.phase1_evaluate_baseline import load_jsonl, summarize

P1 = ROOT / "benchmarks" / "omnirag" / "phase1" / "results"
P2 = ROOT / "benchmarks" / "omnirag" / "phase2" / "results"


def resolve_latest(root: Path) -> Path:
    latest = root / "LATEST"
    if not latest.exists():
        raise SystemExit(f"No LATEST marker under {root}")
    return root / latest.read_text(encoding="utf-8").strip()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--phase1-dir", type=Path)
    p.add_argument("--phase2-dir", type=Path)
    args = p.parse_args()

    p1 = args.phase1_dir or resolve_latest(P1)
    p2 = args.phase2_dir or resolve_latest(P2)
    baseline_summary = json.loads((p1 / "retrieval_summary.json").read_text(encoding="utf-8"))
    rows = load_jsonl(p2 / "retrieval_results.jsonl")
    metrics = summarize(rows)
    routes = Counter((r.get("adaptive") or {}).get("route", "unknown") for r in rows)

    fixed_03 = baseline_summary.get("by_weight", {}).get("0.3", {})
    best_weight = baseline_summary.get("best_weight_by_mrr")
    best_fixed = baseline_summary.get("by_weight", {}).get(f"{float(best_weight):.1f}", {}) if best_weight is not None else {}
    comparison = {
        "phase1_dir": str(p1),
        "phase2_dir": str(p2),
        "adaptive": metrics,
        "route_counts": dict(routes),
        "baseline_0.3": fixed_03,
        "baseline_best_fixed_weight": best_weight,
        "baseline_best_fixed": best_fixed,
        "delta_mrr_vs_0.3": metrics.get("mrr", 0.0) - fixed_03.get("mrr", 0.0),
        "delta_mrr_vs_best_fixed": metrics.get("mrr", 0.0) - best_fixed.get("mrr", 0.0),
        "delta_recall5_vs_0.3": metrics.get("recall@5", 0.0) - fixed_03.get("recall@5", 0.0),
    }
    (p2 / "ADAPTIVE_EVALUATION.json").write_text(json.dumps(comparison, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(comparison, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
