#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs" / "omnirag" / "BASELINE_CORE_HASHES.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def main() -> int:
    expected = json.loads(MANIFEST.read_text(encoding="utf-8"))
    changed = []
    missing = []
    for rel, digest in expected.items():
        path = ROOT / rel
        if not path.exists():
            missing.append(rel)
            continue
        actual = sha256(path)
        if actual != digest:
            changed.append((rel, digest, actual))
    if missing or changed:
        print("Phase-1 core integrity: FAIL")
        for rel in missing:
            print(f"  missing: {rel}")
        for rel, exp, act in changed:
            print(f"  changed: {rel}\n    expected={exp}\n    actual  ={act}")
        return 1
    print(f"Phase-1 core integrity: PASS ({len(expected)} files unchanged)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
