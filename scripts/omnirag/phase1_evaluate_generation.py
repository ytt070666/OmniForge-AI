#!/usr/bin/env python3
"""Evaluate Phase-1 generation output with source-grounding checks.

This evaluator deliberately avoids an LLM-as-judge in the frozen baseline. It
measures whether generation exists and whether the returned reference structure
contains the expected source document. Semantic answer quality can be added as a
separate judge experiment later.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "benchmarks" / "omnirag" / "phase1"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def walk_strings(obj: Any):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield str(k)
            yield from walk_strings(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from walk_strings(v)


def has_expected_source(reference: Any, expected_document: str) -> bool:
    expected = Path(expected_document).name.lower()
    return any(expected in s.lower() for s in walk_strings(reference))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--results-dir", type=Path)
    p.add_argument("--allow-missing", action="store_true", help="return success when chat_results.jsonl was not collected")
    args = p.parse_args()

    if args.results_dir:
        results_dir = args.results_dir
    else:
        latest = BENCH / "results" / "LATEST"
        if not latest.exists():
            if args.allow_missing:
                print("Generation evaluation: SKIP (no Phase-1 LATEST run)")
                return 0
            p.error("no Phase-1 LATEST run")
        results_dir = BENCH / "results" / latest.read_text(encoding="utf-8").strip()

    path = results_dir / "chat_results.jsonl"
    if not path.exists():
        if args.allow_missing:
            print("Generation evaluation: SKIP (chat_results.jsonl not collected)")
            return 0
        p.error(f"missing {path}")

    rows = load_jsonl(path)
    answer_present = [1.0 if str(r.get("answer") or "").strip() else 0.0 for r in rows]
    source_hit = [1.0 if has_expected_source(r.get("reference"), r.get("expected_document", "")) else 0.0 for r in rows]
    latency = [float(r.get("latency_ms", 0.0)) for r in rows]
    summary = {
        "queries": len(rows),
        "answer_presence_rate": mean(answer_present) if rows else 0.0,
        "expected_source_reference_rate": mean(source_hit) if rows else 0.0,
        "mean_latency_ms": mean(latency) if rows else 0.0,
        "note": "This is a deterministic baseline grounding check, not an LLM-as-judge semantic quality score."
    }
    out = results_dir / "generation_summary.json"
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
