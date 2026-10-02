#!/usr/bin/env python3
"""Validate OmniRAG JSON configuration files and required profile invariants."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / "config" / "omnirag" / "model_profiles.json"
RUNTIME = ROOT / "config" / "omnirag" / "runtime_profiles.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    m = load(MODEL)
    r = load(RUNTIME)
    assert m["default_profile"] in m["profiles"]
    assert r["default_profile"] in r["profiles"]
    for name, profile in m["profiles"].items():
        for role in ("chat", "embedding", "rerank"):
            assert role in profile, (name, role)
        assert profile["chat"]["model"]
        assert profile["embedding"]["model"]
    baseline = r["profiles"]["baseline_python_es"]
    assert baseline["api_proxy_scheme"] == "python"
    assert baseline["doc_engine"] == "elasticsearch"
    assert baseline["tei_profile"] == "tei-cpu"
    print(f"model profiles: {len(m['profiles'])}")
    print(f"runtime profiles: {len(r['profiles'])}")
    print("OmniRAG config validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
