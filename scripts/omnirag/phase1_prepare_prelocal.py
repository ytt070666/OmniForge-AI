#!/usr/bin/env python3
"""Prepare a hardware-independent OmniRAG local-run plan without starting services."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODEL_CFG = ROOT / "config" / "omnirag" / "model_profiles.json"
RUNTIME_CFG = ROOT / "config" / "omnirag" / "runtime_profiles.json"
OUT = ROOT / "artifacts" / "omnirag" / "prelocal"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model-profile", default=None)
    p.add_argument("--runtime-profile", default=None)
    args = p.parse_args()

    models = load(MODEL_CFG)
    runtimes = load(RUNTIME_CFG)
    mp = args.model_profile or models["default_profile"]
    rp = args.runtime_profile or runtimes["default_profile"]
    if mp not in models["profiles"]:
        p.error(f"unknown model profile: {mp}")
    if rp not in runtimes["profiles"]:
        p.error(f"unknown runtime profile: {rp}")

    OUT.mkdir(parents=True, exist_ok=True)
    plan = {
        "model_profile": mp,
        "models": models["profiles"][mp],
        "runtime_profile": rp,
        "runtime": runtimes["profiles"][rp],
        "phase_order": [
            "static validation",
            "copy baseline env overlay and set strong local secrets",
            "start RAGFlow dependencies and TEI",
            "configure chat/vision endpoint",
            "run smoke test",
            "collect Phase-1 fixed-weight retrieval baseline",
            "archive Phase-1 manifest/report",
            "apply Phase-2 adaptive patch",
            "run adaptive ablations"
        ],
        "must_remain_disabled_before_baseline": {
            "OMNIRAG_ADAPTIVE_RETRIEVAL": "0",
            "OMNIRAG_EVIDENCE_VERIFIER": "0",
            "OMNIRAG_MEMORY_POLICY": "0"
        }
    }
    (OUT / "PRELOCAL_PLAN.json").write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")

    commands = f"""# Generated plan only. Do not run until the project is moved to the local machine.\n\n# 1. Inspect environment\nbash scripts/omnirag/check_phase1_env.sh\n\n# 2. Static/offline validation\nbash scripts/omnirag/phase1_static_validate.sh\npython3 scripts/omnirag/phase2_policy_preview.py\n\n# 3. Local runtime will use:\n# runtime_profile={rp}\n# model_profile={mp}\n\n# 4. BEFORE baseline, keep feature flags off:\nexport OMNIRAG_ADAPTIVE_RETRIEVAL=0\nexport OMNIRAG_EVIDENCE_VERIFIER=0\nexport OMNIRAG_MEMORY_POLICY=0\n\n# 5. AFTER baseline is archived, apply Phase-2 patch:\npython3 scripts/omnirag/phase2_apply_patch.py --apply\nexport OMNIRAG_ADAPTIVE_RETRIEVAL=1\n"""
    (OUT / "LOCAL_RUN_COMMANDS.txt").write_text(commands, encoding="utf-8")
    print(json.dumps(plan, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
