#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/omnirag/PHASE8_MANIFEST.json"
TRACK = [
    "OMNIRAG.md",
    "config/omnirag/phase8",
    "demos/omnirag/phase8",
    "docs/omnirag/FINAL_README.md",
    "docs/omnirag/FINAL_TECHNICAL_SUMMARY.md",
    "docs/omnirag/JOB_ALIGNMENT_AND_RESUME.md",
    "docs/omnirag/INTERVIEW_PLAYBOOK.md",
    "docs/omnirag/FINAL_LOCAL_EXECUTION_PLAN.md",
    "docs/omnirag/phase8",
    "artifacts/omnirag/phase8",
    "scripts/omnirag/phase8_claims_audit.py",
    "scripts/omnirag/phase8_demo_contracts.py",
    "scripts/omnirag/phase8_release_status.py",
    "scripts/omnirag/phase8_local_master.py",
    "scripts/omnirag/phase8_final_acceptance.py",
    "scripts/omnirag/phase8_generate_manifest.py",
    "scripts/omnirag/phase8_verify_manifest.py",
    "tests/omnirag/test_phase8_release.py"
]

def sha(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()

def iter_files():
    seen = set()
    for rel in TRACK:
        p = ROOT / rel
        items = [p] if p.is_file() else sorted(x for x in p.rglob("*") if x.is_file())
        for item in items:
            r = item.relative_to(ROOT).as_posix()
            if r in seen or r == "docs/omnirag/PHASE8_MANIFEST.json":
                continue
            seen.add(r)
            yield item

def main() -> int:
    files = [{"path": p.relative_to(ROOT).as_posix(), "bytes": p.stat().st_size, "sha256": sha(p)} for p in iter_files()]
    data = {
        "phase": 8,
        "release_stage": "prelocal_ready_v7",
        "runtime_verified": False,
        "live_experiments": "not_run",
        "baseline_core_state": "frozen_unmodified",
        "phase8_core_patch_targets": [],
        "files": files,
        "notes": [
            "Phase 8 adds convergence, portfolio and execution orchestration assets only.",
            "No new RAGFlow core patch is introduced.",
            "Quantitative live claims require committed runtime artifacts."
        ]
    }
    OUT.write_bytes((json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    print(OUT.relative_to(ROOT))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
