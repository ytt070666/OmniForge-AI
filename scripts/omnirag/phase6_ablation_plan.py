#!/usr/bin/env python3
from __future__ import annotations

import json

PLAN = {
    "phase": 6,
    "task": "advisory_control_router",
    "evaluation_sets": ["synthetic_test", "protected_benchmark"],
    "systems": [
        {"name": "rule_baseline", "training": "none", "purpose": "transparent deterministic reference"},
        {"name": "qwen3_0.6b_zero_shot", "training": "none", "purpose": "base-model reference"},
        {"name": "qwen3_0.6b_lora", "training": "LoRA", "purpose": "adapter without base 4-bit quantization"},
        {"name": "qwen3_0.6b_qlora", "training": "QLoRA NF4", "purpose": "memory-efficient adapter"}
    ],
    "metrics": [
        "json_schema_valid_rate",
        "exact_match",
        "query_class_accuracy",
        "retrieval_profile_accuracy",
        "needs_visual_f1",
        "needs_tools_f1",
        "tool_intent_accuracy_on_tool_subset"
    ],
    "promotion_rule": "learned router must pass config/omnirag/phase6/promotion_gate.json on protected benchmark; no automatic core patch",
    "non_claims": [
        "synthetic test is not a production benchmark",
        "passing router evaluation does not prove end-to-end RAG/Agent improvement",
        "router output never authorizes write/execute/open-world tools"
    ]
}
print(json.dumps(PLAN, ensure_ascii=False, indent=2))
