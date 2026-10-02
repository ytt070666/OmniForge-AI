import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_release_policy_is_prelocal_and_fail_closed():
    policy = json.loads((ROOT / "config/omnirag/phase8/release_policy.json").read_text())
    assert policy["release_stage"] == "prelocal_ready"
    assert policy["runtime_verified"] is False
    assert policy["claims_policy"]["allow_live_quality_metrics_without_artifact"] is False
    assert policy["claims_policy"]["allow_upstream_features_as_original_work"] is False


def test_demo_scenarios_have_runtime_boundary():
    scenarios = json.loads((ROOT / "demos/omnirag/phase8/scenarios.json").read_text())
    assert len(scenarios) == 6
    assert any(s["requires_live_runtime"] for s in scenarios)
    assert any(not s["requires_live_runtime"] for s in scenarios)
    assert all(s["success_criteria"] for s in scenarios)


def test_final_docs_keep_not_run_boundary():
    text = (ROOT / "docs/omnirag/FINAL_README.md").read_text().lower()
    assert "not_run" in text
    assert "ragflow" in text
    assert "runtime status" in text


def test_architecture_artifacts_exist():
    assert (ROOT / "artifacts/omnirag/phase8/architecture.svg").stat().st_size > 100
    assert (ROOT / "artifacts/omnirag/phase8/architecture.png").stat().st_size > 100
