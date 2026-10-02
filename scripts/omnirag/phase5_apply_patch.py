#!/usr/bin/env python3
"""Safely check/apply the Phase-5 Agent tool-governance hook.

The Phase-5 patch touches only `agent/component/agent_with_tools.py`. Earlier
Phase-2/3/4 patches do not touch this file, so the expected pre-hash is the
frozen RAGFlow 0.27.2 file hash in both baseline and stacked trees.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / "patches" / "omnirag" / "phase5_tool_governance.patch"
TARGET = ROOT / "agent" / "component" / "agent_with_tools.py"
EXPECTED_PRE_HASH = "181fdb3f2307be50ef18a031b75bcefb4403dc8d706bada63843bd07f480998e"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def patch(dry_run: bool) -> None:
    cmd = ["patch", "-p1", "--forward", "--batch"]
    if dry_run:
        cmd.append("--dry-run")
    cmd += ["-i", str(PATCH)]
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if not PATCH.exists():
        parser.error("Phase-5 patch file is missing")
    if not TARGET.exists():
        parser.error(f"missing target: {TARGET.relative_to(ROOT)}")
    current = sha256(TARGET)
    if current != EXPECTED_PRE_HASH:
        parser.error(
            f"{TARGET.relative_to(ROOT)} is not the reviewed pre-Phase-5 source. "
            f"expected {EXPECTED_PRE_HASH}, got {current}. Do not apply to an unreviewed version."
        )

    patch(True)
    if args.check:
        print("Phase-5 patch check: PASS")
        return 0

    backup_dir = ROOT / "artifacts" / "omnirag" / "patch_backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / f"agent_with_tools.py.pre_phase5.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
    shutil.copy2(TARGET, backup)
    patch(False)
    compile(TARGET.read_text(encoding="utf-8"), str(TARGET), "exec")
    print(f"Phase-5 target sha256 {TARGET.relative_to(ROOT)}: {sha256(TARGET)}")
    print(f"Phase-5 patch applied. Backup: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
