#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs" / "omniai" / "OMNIAI_MANIFEST.json"


def main() -> int:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    errors = []
    for item in data.get("files", []):
        path = ROOT / item["path"]
        if not path.is_file():
            errors.append(f"missing: {item['path']}")
            continue
        raw = path.read_bytes()
        actual = hashlib.sha256(raw).hexdigest()
        if actual != item["sha256"]:
            errors.append(f"hash mismatch: {item['path']}")
        if len(raw) != item["bytes"]:
            errors.append(f"size mismatch: {item['path']}")
    if errors:
        for error in errors:
            print("FAIL:", error)
        return 1
    print(f"OmniAI manifest verification: PASS ({len(data.get('files', []))} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
