#!/usr/bin/env python3
"""Create a no-fabrication status matrix for OmniRAG evaluation artifacts."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts/omnirag/phase6/evaluation_matrix.json"


def latest_dir(root: Path) -> Path | None:
    marker = root / "LATEST"
    if not marker.exists():
        return None
    value = marker.read_text(encoding="utf-8").strip()
    return root / value if value else None


def status(name: str, path: Path | None, metric_scope: str) -> dict:
    exists = bool(path and path.exists())
    return {
        "name": name,
        "status": "available" if exists else "not_run",
        "path": str(path.relative_to(ROOT)) if exists else None,
        "metric_scope": metric_scope,
    }


def main() -> None:
    p1 = latest_dir(ROOT / "benchmarks/omnirag/phase1/results")
    p2 = latest_dir(ROOT / "benchmarks/omnirag/phase2/results")
    rows = [
        status("phase1_retrieval_baseline", p1 / "retrieval_summary.json" if p1 else None, "live RAGFlow retrieval"),
        status("phase2_adaptive_retrieval", p2 / "adaptive_summary.json" if p2 else None, "live adaptive retrieval"),
        status("phase3_multimodal", ROOT / "benchmarks/omnirag/phase3/results/visual_metrics.json", "live multimodal retrieval"),
        status("phase5_tool_selector_smoke", ROOT / "artifacts/omnirag/phase5_tool_selection_smoke.json", "synthetic offline smoke only"),
        status("phase6_rule_router_protected", ROOT / "artifacts/omnirag/phase6/rule_baseline_protected_metrics.json", "protected benchmark deterministic baseline"),
        status("phase6_learned_router_test", ROOT / "artifacts/omnirag/phase6/learned_router_test_metrics.json", "requires actual model inference"),
        status("phase6_learned_router_protected", ROOT / "artifacts/omnirag/phase6/learned_router_protected_metrics.json", "requires actual model inference"),
        status("phase6_system_observability", ROOT / "artifacts/omnirag/phase6/observability_summary.json", "requires live trace events"),
    ]
    payload = {
        "schema_version": 1,
        "rule": "missing artifacts remain not_run; this script never substitutes fabricated metrics",
        "evaluations": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
