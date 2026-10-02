#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYTHON = sys.executable


def run(label: str, command: list[str], *, env: dict[str, str] | None = None) -> None:
    print(f"\n== {label} ==")
    merged = os.environ.copy()
    merged["PYTHONPATH"] = str(ROOT)
    if env:
        merged.update(env)
    subprocess.run(command, cwd=ROOT, env=merged, check=True)


def main() -> int:
    upstreams = json.loads((ROOT / "config/omniai/upstreams.json").read_text(encoding="utf-8"))
    licenses = {item["license"] for item in upstreams["components"]}
    if not licenses <= {"MIT", "Apache-2.0"}:
        raise SystemExit(f"Unexpected upstream license in integration set: {sorted(licenses)}")
    print(f"Upstream inventory: PASS ({len(upstreams['components'])} components; permissive integration set)")

    python_files = []
    for prefix in ("omniai_platform", "services/omniai_gateway", "services/omniai_agent", "services/omniai_llamaindex", "services/omniai_tensorflow", "labs/vector_lab", "labs/tensorflow_lab", "scripts/omniai"):
        python_files.extend(str(path) for path in (ROOT / prefix).rglob("*.py"))
    run("Python compile", [PYTHON, "-m", "py_compile", *python_files])
    run("OmniRAG + OmniAI tests", [PYTHON, "-m", "pytest", "-q", "tests/omnirag", "tests/omniai"])
    run("FastAPI HTTP self-check", [PYTHON, "scripts/omnirag/omniops_selfcheck.py", "--port", "18093"])
    run("Frozen Phase-1 core integrity", [PYTHON, "scripts/omnirag/phase1_verify_core_untouched.py"])
    run("Phase-8 manifest integrity", [PYTHON, "scripts/omnirag/phase8_verify_manifest.py"])
    run("Phase-8 claims audit", [PYTHON, "scripts/omnirag/phase8_claims_audit.py"])

    gofmt = shutil.which("gofmt")
    if gofmt:
        result = subprocess.run([gofmt, "-d", "services/omniai_realtime_go/main.go"], cwd=ROOT, capture_output=True, text=True, check=True)
        if result.stdout.strip():
            print(result.stdout)
            raise SystemExit("Go source is not gofmt-clean")
        print("Go format contract: PASS")
    else:
        print("Go format contract: DEFERRED (gofmt unavailable)")

    run("Generate OmniAI manifest", [PYTHON, "scripts/omniai/generate_manifest.py"])
    run("Verify OmniAI manifest", [PYTHON, "scripts/omniai/verify_manifest.py"])

    print("\nOptional runtime checks are tracked in artifacts/runtime/FINAL_RUNTIME_REPORT.md.")
    print("\nOmniAI modular platform static/in-process validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
