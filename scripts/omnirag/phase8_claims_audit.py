#!/usr/bin/env python3
from __future__ import annotations
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = [
    ROOT / "docs/omnirag/FINAL_README.md",
    ROOT / "docs/omnirag/FINAL_TECHNICAL_SUMMARY.md",
    ROOT / "docs/omnirag/JOB_ALIGNMENT_AND_RESUME.md",
    ROOT / "docs/omnirag/INTERVIEW_PLAYBOOK.md",
]
FORBIDDEN = [
    re.compile(r"runtime verified\s*[:=]\s*true", re.I),
    re.compile(r"docker(?:\s+compose)?\s+(?:runtime|deployment).*\bpass\b", re.I),
    re.compile(r"kubernetes.*\bpass\b", re.I),
    re.compile(r"agent success rate\s*[:=]\s*\d", re.I),
]
REQUIRED_PHRASES = ["pre-local", "not_run", "RAGFlow"]

def main() -> int:
    missing = [str(p.relative_to(ROOT)) for p in DOCS if not p.exists()]
    if missing:
        raise SystemExit(f"missing final docs: {missing}")
    text = "\n".join(p.read_text(encoding="utf-8") for p in DOCS)
    hits = [pat.pattern for pat in FORBIDDEN if pat.search(text)]
    if hits:
        raise SystemExit(f"claims audit failed: forbidden unverified claims matched: {hits}")
    for phrase in REQUIRED_PHRASES:
        if phrase.lower() not in text.lower():
            raise SystemExit(f"claims audit failed: required boundary phrase missing: {phrase}")
    print("Phase-8 claims audit: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
