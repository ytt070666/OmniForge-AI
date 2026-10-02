#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs/omnirag/PHASE8_MANIFEST.json"

def sha(p: Path) -> str:
    h = hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()

def main() -> int:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert data["runtime_verified"] is False
    assert data["live_experiments"] == "not_run"
    for entry in data["files"]:
        p = ROOT / entry["path"]
        if not p.exists():
            raise SystemExit(f"manifest missing file: {entry['path']}")
        if p.stat().st_size != entry["bytes"] or sha(p) != entry["sha256"]:
            raise SystemExit(f"manifest hash mismatch: {entry['path']}")
    print(f"Phase-8 manifest verification: PASS ({len(data['files'])} files)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
