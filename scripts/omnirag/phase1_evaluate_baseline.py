#!/usr/bin/env python3
"""Evaluate OmniRAG-Agent Phase-1 retrieval results.

The evaluator reports document-level Recall@K, MRR, NDCG@K, latency, and score
statistics for each fixed vector similarity weight and for each query category.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BENCH = ROOT / "benchmarks" / "omnirag" / "phase1"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            rows.append(json.loads(raw))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid JSON in {path}:{line_no}: {exc}") from exc
    return rows


def norm_name(value: Any) -> str:
    if value is None:
        return ""
    return Path(str(value).strip()).name.lower()


def chunk_relevant(chunk: dict[str, Any], expected_doc: str, markers: list[str]) -> bool:
    expected = norm_name(expected_doc)
    actual = norm_name(chunk.get("document_keyword"))
    if actual and (actual == expected or expected in actual or actual in expected):
        return True
    content = str(chunk.get("content") or "").lower()
    if markers and any(str(marker).lower() in content for marker in markers):
        return True
    return False


def relevance_rank(row: dict[str, Any]) -> int | None:
    expected = row.get("expected_document", "")
    markers = row.get("expected_markers") or []
    for idx, chunk in enumerate(row.get("chunks") or [], start=1):
        if chunk_relevant(chunk, expected, markers):
            return idx
    return None


def dcg_single(rank: int | None, k: int) -> float:
    if rank is None or rank > k:
        return 0.0
    return 1.0 / math.log2(rank + 1)


def safe_mean(values: list[float]) -> float:
    return mean(values) if values else 0.0


def summarize(rows: list[dict[str, Any]], ks: tuple[int, ...] = (1, 3, 5, 10)) -> dict[str, Any]:
    ranks = [relevance_rank(row) for row in rows]
    latencies = [float(row.get("latency_ms", 0.0)) for row in rows]
    metrics: dict[str, Any] = {
        "queries": len(rows),
        "mrr": safe_mean([0.0 if r is None else 1.0 / r for r in ranks]),
        "mean_latency_ms": safe_mean(latencies),
        "median_latency_ms": median(latencies) if latencies else 0.0,
        "misses": sum(1 for r in ranks if r is None),
    }
    for k in ks:
        metrics[f"recall@{k}"] = safe_mean([1.0 if r is not None and r <= k else 0.0 for r in ranks])
        metrics[f"ndcg@{k}"] = safe_mean([dcg_single(r, k) for r in ranks])

    top_scores: list[float] = []
    top_term_scores: list[float] = []
    top_vector_scores: list[float] = []
    for row in rows:
        chunks = row.get("chunks") or []
        if not chunks:
            continue
        first = chunks[0]
        for key, dest in (
            ("similarity", top_scores),
            ("term_similarity", top_term_scores),
            ("vector_similarity", top_vector_scores),
        ):
            value = first.get(key)
            if isinstance(value, (int, float)):
                dest.append(float(value))
    metrics["mean_top_similarity"] = safe_mean(top_scores)
    metrics["mean_top_term_similarity"] = safe_mean(top_term_scores)
    metrics["mean_top_vector_similarity"] = safe_mean(top_vector_scores)
    return metrics


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def f3(value: float) -> str:
    return f"{value:.3f}"


def write_markdown(summary: dict[str, Any], out: Path) -> None:
    lines = [
        "# OmniRAG-Agent Phase-1 Baseline Retrieval Report",
        "",
        "This report is generated from the untouched RAGFlow 0.27.2 retrieval API. No OmniRAG retrieval innovation is enabled.",
        "",
        "## Overall weight sweep",
        "",
        "| Vector weight | Term weight | Queries | Recall@1 | Recall@3 | Recall@5 | MRR | NDCG@5 | Mean latency (ms) | Misses |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for weight_str, metrics in summary["by_weight"].items():
        weight = float(weight_str)
        lines.append(
            f"| {weight:.1f} | {1-weight:.1f} | {metrics['queries']} | {pct(metrics['recall@1'])} | {pct(metrics['recall@3'])} | "
            f"{pct(metrics['recall@5'])} | {f3(metrics['mrr'])} | {f3(metrics['ndcg@5'])} | {metrics['mean_latency_ms']:.1f} | {metrics['misses']} |"
        )

    best = summary.get("best_weight_by_mrr")
    lines += [
        "",
        "## Baseline interpretation",
        "",
        f"- Best fixed vector weight by MRR in this run: **{best}**." if best is not None else "- No best weight could be selected.",
        "- RAGFlow's default-style fixed hybrid setting is represented by vector weight **0.3**.",
        "- Differences between lexical, semantic, and cross-lingual groups are the evidence we will use to justify a query-adaptive fusion policy in Phase 2.",
        "",
        "## Category breakdown",
        "",
    ]

    categories = summary.get("by_weight_and_category", {})
    for weight_str in sorted(categories, key=float):
        lines.append(f"### Vector weight {float(weight_str):.1f}")
        lines.append("")
        lines.append("| Category | Queries | Recall@1 | Recall@5 | MRR | NDCG@5 | Mean latency (ms) |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|")
        for category, metrics in sorted(categories[weight_str].items()):
            lines.append(
                f"| {category} | {metrics['queries']} | {pct(metrics['recall@1'])} | {pct(metrics['recall@5'])} | "
                f"{f3(metrics['mrr'])} | {f3(metrics['ndcg@5'])} | {metrics['mean_latency_ms']:.1f} |"
            )
        lines.append("")

    lines += [
        "## Phase-2 gate",
        "",
        "Do not modify `rag/nlp/search.py` until this report has been generated successfully from a live RAGFlow deployment and archived with the matching `run_manifest.json`.",
        "",
    ]
    out.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, help="directory containing retrieval_results.jsonl; defaults to benchmarks/.../results/LATEST")
    args = parser.parse_args()

    if args.results_dir:
        results_dir = args.results_dir
    else:
        latest_file = DEFAULT_BENCH / "results" / "LATEST"
        if not latest_file.exists():
            parser.error("No --results-dir supplied and no LATEST baseline run exists")
        run_id = latest_file.read_text(encoding="utf-8").strip()
        results_dir = DEFAULT_BENCH / "results" / run_id

    retrieval_file = results_dir / "retrieval_results.jsonl"
    if not retrieval_file.exists():
        parser.error(f"Missing {retrieval_file}")

    rows = load_jsonl(retrieval_file)
    if not rows:
        parser.error("retrieval_results.jsonl is empty")

    by_weight_rows: dict[float, list[dict[str, Any]]] = defaultdict(list)
    by_weight_cat_rows: dict[float, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        weight = float(row["vector_similarity_weight"])
        by_weight_rows[weight].append(row)
        by_weight_cat_rows[weight][str(row.get("category", "unknown"))].append(row)

    by_weight = {f"{w:.1f}": summarize(group) for w, group in sorted(by_weight_rows.items())}
    by_weight_and_category = {
        f"{w:.1f}": {cat: summarize(group) for cat, group in sorted(cats.items())}
        for w, cats in sorted(by_weight_cat_rows.items())
    }
    best_weight = None
    if by_weight:
        best_weight = max(by_weight, key=lambda key: (by_weight[key]["mrr"], by_weight[key]["recall@1"], -float(key)))

    summary = {
        "result_file": str(retrieval_file),
        "rows": len(rows),
        "weights": [float(w) for w in sorted(by_weight_rows)],
        "best_weight_by_mrr": float(best_weight) if best_weight is not None else None,
        "by_weight": by_weight,
        "by_weight_and_category": by_weight_and_category,
    }

    summary_json = results_dir / "retrieval_summary.json"
    summary_md = results_dir / "BASELINE_REPORT.md"
    summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(summary, summary_md)

    print(f"Wrote {summary_json}")
    print(f"Wrote {summary_md}")
    print("\nWeight sweep:")
    for weight, metrics in by_weight.items():
        print(
            f"  wv={weight}: R@1={metrics['recall@1']:.3f} R@5={metrics['recall@5']:.3f} "
            f"MRR={metrics['mrr']:.3f} NDCG@5={metrics['ndcg@5']:.3f} latency={metrics['mean_latency_ms']:.1f}ms"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
