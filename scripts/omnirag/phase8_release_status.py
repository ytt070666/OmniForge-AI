#!/usr/bin/env python3
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts/omnirag/phase8/final_release_status.json"

def exists(rel: str) -> bool:
    return (ROOT / rel).exists()

def main() -> int:
    status = {
        "project": "OmniRAG-Agent",
        "upstream": "RAGFlow v0.27.2",
        "stage": "prelocal_ready_v7",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "runtime_verified": False,
        "static_validation": "pass",
        "core_baseline": "frozen_unmodified",
        "live_experiments": "not_run",
        "docker_runtime": "not_run",
        "kubernetes_apply": "not_run",
        "gpu_models": "not_run",
        "deliverables": {
            "final_readme": exists("docs/omnirag/FINAL_README.md"),
            "technical_summary": exists("docs/omnirag/FINAL_TECHNICAL_SUMMARY.md"),
            "resume_pack": exists("docs/omnirag/JOB_ALIGNMENT_AND_RESUME.md"),
            "interview_playbook": exists("docs/omnirag/INTERVIEW_PLAYBOOK.md"),
            "local_master_runbook": exists("docs/omnirag/FINAL_LOCAL_EXECUTION_PLAN.md"),
            "architecture_svg": exists("artifacts/omnirag/phase8/architecture.svg"),
            "demo_scenarios": exists("demos/omnirag/phase8/scenarios.json")
        }
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes((json.dumps(status, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    print(OUT.relative_to(ROOT))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
