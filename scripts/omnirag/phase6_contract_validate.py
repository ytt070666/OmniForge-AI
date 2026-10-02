#!/usr/bin/env python3
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def main() -> None:
    dataset = load("benchmarks/omnirag/phase6/router/dataset_manifest.json")
    report = dataset["leakage_report"]
    assert report["counts"] == {"train": 168, "validation": 48, "test": 48, "protected": 56}
    assert not any(report["family_collisions"].values())
    assert not any(report["prompt_collision_counts"].values())
    assert report["protected_exact_overlap_train"] == 0
    assert report["protected_exact_overlap_validation"] == 0
    assert report["protected_train_max_5gram_overlap"] <= 0.60
    assert dataset["protected_sources_used_for_training"] is False

    cfg = load("config/omnirag/phase6/router_sft.json")
    assert cfg["method"] == "qlora"
    assert cfg["model_name_or_path"] == "Qwen/Qwen3-0.6B"
    assert cfg["lora"]["target_modules"] == "all-linear"
    assert cfg["qlora"]["bnb_4bit_quant_type"] == "nf4"
    assert cfg["safety_boundary"] == {
        "advisory_only": True,
        "may_authorize_execute_tools": False,
        "may_authorize_write_tools": False,
        "may_bypass_phase5_policy": False,
        "may_replace_phase3_evidence_verifier": False,
    }

    obs = load("config/omnirag/phase6/observability.json")
    assert obs["capture_raw_prompt"] is False
    assert obs["capture_raw_completion"] is False
    assert obs["capture_tool_arguments"] is False
    assert obs["capture_retrieved_chunk_text"] is False
    assert obs["costing"]["enabled"] is False

    gate = load("config/omnirag/phase6/promotion_gate.json")
    assert gate["policy"] == "fail_closed"
    assert gate["integration_boundary"]["automatic_core_patch_on_gate_pass"] is False
    assert gate["integration_boundary"]["phase5_policy_remains_authoritative"] is True
    assert gate["integration_boundary"]["phase3_verifier_remains_authoritative"] is True

    protected = load("artifacts/omnirag/phase6/rule_baseline_protected_metrics.json")
    test = load("artifacts/omnirag/phase6/rule_baseline_test_metrics.json")
    assert protected["total"] == 56 and test["total"] == 48
    assert math.isclose(protected["json_schema_valid_rate"], 1.0)
    assert protected["exact_match"] > 0.70
    assert test["exact_match"] > 0.65

    matrix = load("artifacts/omnirag/phase6/evaluation_matrix.json")
    by_name = {row["name"]: row for row in matrix["evaluations"]}
    assert by_name["phase6_learned_router_test"]["status"] == "not_run"
    assert by_name["phase6_learned_router_protected"]["status"] == "not_run"
    assert by_name["phase6_system_observability"]["status"] == "not_run"

    assert not (ROOT / "patches/omnirag/phase6_posttraining.patch").exists()
    print("PASS: Phase-6 contracts preserve data isolation, advisory safety, no-fabrication evaluation and no core patch")


if __name__ == "__main__":
    main()
