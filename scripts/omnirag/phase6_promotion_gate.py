#!/usr/bin/env python3
"""Fail-closed promotion gate for the learned advisory router.

Passing this gate only permits later integration experiments. It never patches
RAGFlow and never grants tool authorization.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def metric(report: dict, key: str) -> float:
    if key == "query_class":
        return float(report["field_accuracy"]["query_class"])
    if key == "needs_visual_f1":
        return float(report["needs_visual"]["f1"])
    if key == "needs_tools_f1":
        return float(report["needs_tools"]["f1"])
    if key == "tool_intent":
        value = report["tool_intent_accuracy_on_tool_subset"]
        return float(value) if value is not None else 0.0
    raise KeyError(key)


def evaluate(rule: dict, learned: dict, cfg: dict) -> tuple[bool, list[dict]]:
    checks = []
    req = cfg["required"]
    checks.append({
        "name": "json_schema_valid_rate",
        "passed": float(learned["json_schema_valid_rate"]) >= float(req["json_schema_valid_rate"]),
        "value": learned["json_schema_valid_rate"],
        "threshold": req["json_schema_valid_rate"],
    })
    pairs = [
        ("query_class", "min_query_class_gain_vs_rule_baseline"),
        ("needs_visual_f1", "min_needs_visual_f1_gain_vs_rule_baseline"),
        ("needs_tools_f1", "min_needs_tools_f1_gain_vs_rule_baseline"),
        ("tool_intent", "min_tool_intent_gain_vs_rule_baseline"),
    ]
    max_reg = float(req["max_regression_vs_rule_baseline"])
    for name, gain_key in pairs:
        base = metric(rule, name)
        new = metric(learned, name)
        gain = new - base
        min_gain = float(req[gain_key])
        checks.append({"name": name, "passed": gain >= min_gain and gain >= -max_reg, "baseline": base, "learned": new, "gain": gain, "min_gain": min_gain})
    return all(item["passed"] for item in checks), checks


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--rule", default="artifacts/omnirag/phase6/rule_baseline_protected_metrics.json")
    p.add_argument("--learned", default="artifacts/omnirag/phase6/learned_router_protected_metrics.json")
    p.add_argument("--config", default="config/omnirag/phase6/promotion_gate.json")
    p.add_argument("--check-config-only", action="store_true")
    args = p.parse_args()
    cfg = load(args.config)
    boundary = cfg["integration_boundary"]
    assert boundary["router_is_advisory"] is True
    assert boundary["phase5_policy_remains_authoritative"] is True
    assert boundary["phase3_verifier_remains_authoritative"] is True
    assert boundary["automatic_core_patch_on_gate_pass"] is False
    if args.check_config_only:
        print("PASS: promotion gate config is fail-closed and does not authorize automatic integration")
        return
    learned_path = ROOT / args.learned
    if not learned_path.exists():
        raise SystemExit("NOT_RUN: learned metrics are missing; router cannot be promoted")
    ok, checks = evaluate(load(args.rule), load(args.learned), cfg)
    print(json.dumps({"passed": ok, "checks": checks}, ensure_ascii=False, indent=2))
    if not ok:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
