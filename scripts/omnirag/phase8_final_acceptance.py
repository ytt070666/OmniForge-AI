#!/usr/bin/env python3
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECKS = [
    [sys.executable, "scripts/omnirag/phase7_static_validate.py"],
    [sys.executable, "scripts/omnirag/phase8_demo_contracts.py"],
    [sys.executable, "scripts/omnirag/phase8_claims_audit.py"],
    [sys.executable, "scripts/omnirag/phase8_release_status.py"],
    [sys.executable, "scripts/omnirag/phase8_generate_manifest.py"],
    [sys.executable, "scripts/omnirag/phase8_verify_manifest.py"],
]

def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)

def main() -> int:
    for cmd in CHECKS:
        run(cmd)
    status_path = ROOT / "artifacts/omnirag/phase8/final_release_status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert status["runtime_verified"] is False
    assert status["live_experiments"] == "not_run"
    assert all(status["deliverables"].values())
    print("Phase-8 final pre-local acceptance: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
