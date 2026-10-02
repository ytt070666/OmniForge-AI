#!/usr/bin/env python3
"""Summarize online Phase-3 retrieval, answer, and persistence evidence."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def first_rank(expected: set[str], ranked: list[str]) -> int | None:
    return next((i for i, chunk_id in enumerate(ranked, start=1) if chunk_id in expected), None)


def metric(rows: list[dict], key: str) -> dict:
    ranks = [first_rank(set(row["expected_chunk_ids"]), row.get(key) or []) for row in rows]
    n = len(rows)
    return {
        "count": n,
        "Recall@1": sum(rank == 1 for rank in ranks) / n,
        "Recall@3": sum(rank is not None and rank <= 3 for rank in ranks) / n,
        "Recall@5": sum(rank is not None and rank <= 5 for rank in ranks) / n,
        "MRR": sum(1 / rank for rank in ranks if rank is not None) / n,
        "all_required_at_5": sum(set(row["expected_chunk_ids"]).issubset(set((row.get(key) or [])[:5])) for row in rows) / n,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    all_rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    latest = {row["query_id"]: row for row in all_rows}
    successful = [row for row in latest.values() if row.get("completed") and row.get("answer", "").strip() and not row["answer"].startswith("**ERROR**")]
    by_category = defaultdict(list)
    for row in successful:
        row["fused_chunk_ids"] = [chunk.get("id") or chunk.get("chunk_id") for chunk in (row.get("reference") or {}).get("chunks", [])]
        by_category[row["category"]].append(row)
    decisions = Counter((row.get("verification") or {}).get("decision", "missing") for row in successful)
    fallback_phrases = ("the answer you are looking for is not found in the dataset", "未找到足够证据", "无相关内容")
    contradictions = [row["query_id"] for row in successful if any(phrase in row["answer"].casefold() for phrase in fallback_phrases)]
    marker_and_no_fallback = sum(bool(row.get("answer_markers_all_present")) and row["query_id"] not in contradictions for row in successful)
    report = {
        "scope": "online RAGFlow Phase-3; six synthetic images, 18 protected questions",
        "attempt_rows": len(all_rows),
        "unique_queries": len(latest),
        "successful_queries": len(successful),
        "failed_queries": {row["query_id"]: row.get("error") for row in latest.values() if not row.get("completed")},
        "answer_markers_all_present": sum(bool(row.get("answer_markers_all_present")) for row in successful),
        "answer_markers_without_fallback": marker_and_no_fallback,
        "contradictory_not_found_query_ids": contradictions,
        "verifier_persisted_count": sum(bool(row.get("verification_persisted")) for row in successful),
        "verifier_decisions": dict(decisions),
        "visual_retrieval": metric(successful, "visual_hit_chunk_ids") if successful else {},
        "fused_reference": metric(successful, "fused_chunk_ids") if successful else {},
        "categories": {name: metric(rows, "visual_hit_chunk_ids") for name, rows in sorted(by_category.items())},
        "limitations": [
            "The images are synthetic benchmark assets, not public or enterprise production documents.",
            "Marker presence and marker_without_fallback are string checks, not human correctness judgments.",
            "Contradictory fallback text makes an answer unsuitable even if its markers are present.",
            "Reference chunks are the persisted citation set; visual_hit_chunk_ids are the actual sidecar retrieval order.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("unique_queries", "successful_queries", "answer_markers_all_present", "verifier_persisted_count", "verifier_decisions", "visual_retrieval", "fused_reference")}, ensure_ascii=False, indent=2))
    return 0 if len(successful) == 18 else 1


if __name__ == "__main__":
    raise SystemExit(main())
