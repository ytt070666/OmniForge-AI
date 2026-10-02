"""Deterministic evaluation metrics for structured router predictions."""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from .schema import REQUIRED_OUTPUT_KEYS, RouterSchemaError, validate_router_output


def _binary_prf(golds: list[bool], preds: list[bool]) -> dict[str, float]:
    tp = sum(g and p for g, p in zip(golds, preds))
    fp = sum((not g) and p for g, p in zip(golds, preds))
    fn = sum(g and (not p) for g, p in zip(golds, preds))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def evaluate_router_rows(golds: list[dict[str, Any]], predictions: list[dict[str, Any]]) -> dict[str, Any]:
    pred_by_id = {row["id"]: row for row in predictions}
    total = len(golds)
    parsed = 0
    field_correct = Counter()
    exact = 0
    tool_golds: list[str] = []
    tool_preds: list[str] = []
    visual_golds: list[bool] = []
    visual_preds: list[bool] = []
    tools_golds: list[bool] = []
    tools_preds: list[bool] = []
    failures = []

    for gold in golds:
        raw = pred_by_id.get(gold["id"], {}).get("prediction")
        if raw is None:
            failures.append({"id": gold["id"], "reason": "missing_prediction"})
            continue
        try:
            value = json.loads(raw) if isinstance(raw, str) else raw
            validate_router_output(value)
        except (json.JSONDecodeError, RouterSchemaError, TypeError) as exc:
            failures.append({"id": gold["id"], "reason": type(exc).__name__})
            continue
        parsed += 1
        expected = json.loads(gold["completion"])
        if value == expected:
            exact += 1
        for key in REQUIRED_OUTPUT_KEYS:
            if value[key] == expected[key]:
                field_correct[key] += 1
        visual_golds.append(expected["needs_visual"])
        visual_preds.append(value["needs_visual"])
        tools_golds.append(expected["needs_tools"])
        tools_preds.append(value["needs_tools"])
        if expected["needs_tools"]:
            tool_golds.append(expected["tool_intent"])
            tool_preds.append(value["tool_intent"])

    denom = max(1, total)
    return {
        "total": total,
        "parsed_valid": parsed,
        "json_schema_valid_rate": parsed / denom,
        "exact_match": exact / denom,
        "field_accuracy": {key: field_correct[key] / denom for key in REQUIRED_OUTPUT_KEYS},
        "needs_visual": _binary_prf(visual_golds, visual_preds),
        "needs_tools": _binary_prf(tools_golds, tools_preds),
        "tool_intent_accuracy_on_tool_subset": (
            sum(g == p for g, p in zip(tool_golds, tool_preds)) / len(tool_golds) if tool_golds else None
        ),
        "failures": failures,
    }
