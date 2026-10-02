#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = ROOT / "demos/omnirag/phase8/scenarios.json"

def main() -> int:
    data = json.loads(SCENARIOS.read_text(encoding="utf-8"))
    assert len(data) == 6
    ids = [x["id"] for x in data]
    assert len(ids) == len(set(ids))
    assert all(x.get("success_criteria") for x in data)
    assert all(isinstance(x.get("requires_live_runtime"), bool) for x in data)
    offline = [x for x in data if not x["requires_live_runtime"]]
    assert any(x["id"] == "D5" for x in offline)
    print("Phase-8 demo contracts: PASS (6 scenarios; live-only claims remain deferred)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
