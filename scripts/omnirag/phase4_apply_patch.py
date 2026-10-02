#!/usr/bin/env python3
"""Safely check/apply the OmniRAG Phase-4 agent-governance integration patch.

Application order is intentional:
  Phase 1 frozen source -> Phase 2 -> Phase 3 -> Phase 4

Phase 4 refuses to apply unless dialog_service.py is already in the exact
Phase-3-applied state and agentic_rag.py is the frozen RAGFlow 0.27.2 source.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / "patches" / "omnirag" / "phase4_memory_agent_governance.patch"
TARGETS = {
    ROOT / "api" / "db" / "services" / "dialog_service.py": "1b58db3e6193e7e23ce98ab80a48bc1acc158191bfa05ae808dcfc26bdd2998c",
    ROOT / "rag" / "advanced_rag" / "agentic_rag.py": "75fd5ee92387f7c44f063ee332b6d355622c3ff27b69c79a2e5dd95233138b23",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _patch(dry_run: bool) -> None:
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
        parser.error("Phase-4 patch file is missing")
    for target, expected in TARGETS.items():
        if not target.exists():
            parser.error(f"missing target: {target.relative_to(ROOT)}")
        current = sha256(target)
        if current != expected:
            parser.error(
                f"{target.relative_to(ROOT)} is not in the required pre-Phase-4 state. "
                f"expected {expected}, got {current}. Apply Phase 3 first and do not edit core files manually."
            )

    _patch(True)
    if args.check:
        print("Phase-4 patch check: PASS")
        return 0

    backup_dir = ROOT / "artifacts" / "omnirag" / "patch_backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    for target in TARGETS:
        backup = backup_dir / f"{target.name}.pre_phase4.{stamp}.bak"
        shutil.copy2(target, backup)
    _patch(False)
    for target in TARGETS:
        compile(target.read_text(encoding="utf-8"), str(target), "exec")
        print(f"Phase-4 target sha256 {target.relative_to(ROOT)}: {sha256(target)}")
    print(f"Phase-4 patch applied. Backups: {backup_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
