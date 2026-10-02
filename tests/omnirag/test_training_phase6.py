import json
from pathlib import Path

import pytest

from extensions.omnirag.training.dataset import assert_no_leakage, leakage_report, load_jsonl
from extensions.omnirag.training.metrics import evaluate_router_rows
from extensions.omnirag.training.redaction import findings, redact
from extensions.omnirag.training.schema import RouterSchemaError, make_completion, validate_router_output

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "benchmarks/omnirag/phase6/router"


def test_router_schema_is_closed_and_advisory_shape_only():
    good = json.loads(make_completion(query_class="semantic", retrieval_profile="dense_heavy"))
    assert validate_router_output(good) == good
    bad = dict(good)
    bad["authorize_write"] = True
    with pytest.raises(RouterSchemaError):
        validate_router_output(bad)


def test_tool_schema_requires_consistent_intent():
    with pytest.raises(RouterSchemaError):
        validate_router_output(
            {
                "query_class": "tool",
                "retrieval_profile": "balanced",
                "needs_visual": False,
                "needs_tools": True,
                "tool_intent": "none",
                "evidence_strictness": "high",
            }
        )


def test_phase6_dataset_has_family_level_isolation_and_no_protected_leak():
    splits = {name: load_jsonl(DATA / f"{name}.jsonl") for name in ("train", "validation", "test")}
    protected = load_jsonl(DATA / "protected_benchmark.jsonl")
    report = leakage_report(splits, protected)
    assert_no_leakage(report)
    assert report["counts"] == {"train": 168, "validation": 48, "test": 48, "protected": 56}
    assert report["protected_exact_overlap_train"] == 0
    assert report["protected_exact_overlap_validation"] == 0
    manifest = json.loads((DATA / "dataset_manifest.json").read_text(encoding="utf-8"))
    assert manifest["leakage_report"]["protected_train_max_5gram_overlap"] <= 0.60


def test_hygiene_detects_and_redacts_secret_like_material():
    sample = "email admin@example.com Bearer abcdefghijklmnopqrstuvwxyz123"
    kinds = {item.kind for item in findings(sample)}
    assert {"email", "bearer"} <= kinds
    cleaned = redact(sample)
    assert "admin@example.com" not in cleaned
    assert "Bearer abc" not in cleaned


def test_structured_metrics_count_invalid_json_as_failure():
    gold = load_jsonl(DATA / "test.jsonl")[:2]
    preds = [
        {"id": gold[0]["id"], "prediction": gold[0]["completion"]},
        {"id": gold[1]["id"], "prediction": "not-json"},
    ]
    report = evaluate_router_rows(gold, preds)
    assert report["json_schema_valid_rate"] == 0.5
    assert len(report["failures"]) == 1
