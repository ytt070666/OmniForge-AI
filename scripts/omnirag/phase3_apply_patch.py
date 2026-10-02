#!/usr/bin/env python3
"""Safely check/apply the OmniRAG Phase-3 multimodal/verifier integration patch."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "api" / "db" / "services" / "dialog_service.py"
PATCH = ROOT / "patches" / "omnirag" / "phase3_multimodal_verifier.patch"
EXPECTED_SHA256 = "22be233dd35f50af41b406104e8a046363296c6327bf0e97d6e438121f9d842b"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_patch(dry_run: bool) -> None:
    cmd = ["patch", "-p1", "--forward", "--batch"]
    if dry_run:
        cmd.append("--dry-run")
    cmd += ["-i", str(PATCH)]
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--apply", action="store_true")
    args = p.parse_args()
    if not TARGET.exists() or not PATCH.exists():
        p.error("target or patch file is missing")
    current = sha256(TARGET)
    if current != EXPECTED_SHA256:
        p.error(
            "dialog_service.py is not the frozen RAGFlow 0.27.2 baseline. "
            f"expected {EXPECTED_SHA256}, got {current}. Refusing to patch."
        )
    run_patch(True)
    if args.check:
        print("Phase-3 patch check: PASS")
        return 0
    backup_dir = ROOT / "artifacts" / "omnirag" / "patch_backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / f"dialog_service.py.phase1.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
    shutil.copy2(TARGET, backup)
    run_patch(False)
    compile(TARGET.read_text(encoding="utf-8"), str(TARGET), "exec")
    print(f"Phase-3 patch applied. Backup: {backup}")
    print(f"New dialog_service.py sha256: {sha256(TARGET)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
