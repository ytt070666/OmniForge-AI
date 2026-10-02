#!/usr/bin/env python3
"""Safely apply/check the OmniRAG Phase-2 adaptive retrieval patch.

The script refuses to patch a source file that does not match the frozen Phase-1
RAGFlow 0.27.2 baseline hash. This prevents accidental patching of a different
upstream revision.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "rag" / "nlp" / "search.py"
PATCH = ROOT / "patches" / "omnirag" / "phase2_adaptive_retrieval.patch"
EXPECTED_SHA256 = "e11c2aa749db1a44d0698f3cdda9b85c0519a5919e05d173fec793dfca3b9387"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_patch(dry_run: bool) -> None:
    cmd = ["patch", "-p1", "--forward", "--batch"]
    if dry_run:
        cmd.append("--dry-run")
    cmd += ["-i", str(PATCH)]
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> int:
    p = argparse.ArgumentParser()
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--apply", action="store_true")
    args = p.parse_args()

    if not TARGET.exists() or not PATCH.exists():
        p.error("target or patch file is missing")

    current = sha256(TARGET)
    if current != EXPECTED_SHA256:
        p.error(
            "rag/nlp/search.py is not the frozen Phase-1 baseline. "
            f"expected {EXPECTED_SHA256}, got {current}. Refusing to patch."
        )

    run_patch(dry_run=True)
    if args.check:
        print("Phase-2 patch check: PASS")
        return 0

    backup_dir = ROOT / "artifacts" / "omnirag" / "patch_backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / f"search.py.phase1.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
    shutil.copy2(TARGET, backup)
    run_patch(dry_run=False)
    compile(TARGET.read_text(encoding="utf-8"), str(TARGET), "exec")
    print(f"Phase-2 patch applied. Backup: {backup}")
    print(f"New search.py sha256: {sha256(TARGET)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
