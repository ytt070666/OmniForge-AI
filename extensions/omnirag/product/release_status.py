from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def build_release_status(root: Path) -> dict[str, Any]:
    matrix_path = root / "artifacts/omnirag/phase6/evaluation_matrix.json"
    matrix = load_json(matrix_path) if matrix_path.exists() else {"evaluations": []}
    evaluations = matrix.get("evaluations", [])
    live = [row for row in evaluations if row.get("status") == "available" and "live" in str(row.get("metric_scope", ""))]
    not_run = [row for row in evaluations if row.get("status") != "available"]
    return {
        "schema_version": 1,
        "release_stage": "prelocal_ready",
        "runtime_verified": False,
        "live_evaluation_count": len(live),
        "not_run_evaluation_count": len(not_run),
        "rule": "Pre-local artifacts never imply live RAGFlow/GPU validation.",
        "evaluations": evaluations,
    }
