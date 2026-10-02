#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = [
    ("static", "python3 scripts/omnirag/phase8_final_acceptance.py"),
    ("env", "bash scripts/omnirag/check_phase1_env.sh"),
    ("baseline", "bash scripts/omnirag/phase1_acceptance.sh"),
    ("phase2", "python3 scripts/omnirag/phase2_ablation_plan.py"),
    ("phase3", "python3 scripts/omnirag/phase3_ablation_plan.py"),
    ("phase4", "bash scripts/omnirag/phase4_static_validate.sh"),
    ("phase5", "bash scripts/omnirag/phase5_static_validate.sh"),
    ("phase6", "bash scripts/omnirag/phase6_static_validate.sh"),
    ("phase7", "python3 scripts/omnirag/phase7_static_validate.py"),
]

def main() -> int:
    ap = argparse.ArgumentParser(description="OmniRAG final local execution planner; it does not start services by default.")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    data = {
        "stage": "prelocal_ready",
        "runtime_verified": False,
        "docker_available": bool(shutil.which("docker")),
        "kubectl_available": bool(shutil.which("kubectl")),
        "steps": [{"gate": gate, "command": cmd} for gate, cmd in PLAN],
        "note": "This is a plan only. Execute gates manually in order so baseline and ablations remain isolated."
    }
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print("OmniRAG final local plan (no commands executed):")
        for i, (gate, cmd) in enumerate(PLAN, 1):
            print(f"{i:02d}. {gate:10s} {cmd}")
        print("Runtime verified: false")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
