#!/usr/bin/env python3
"""Fail closed when a Docker base image does not match the reviewed RAGFlow source."""
from __future__ import annotations
import argparse, hashlib
from pathlib import Path

PRE = {
    "rag/nlp/search.py": "e11c2aa749db1a44d0698f3cdda9b85c0519a5919e05d173fec793dfca3b9387",
    "api/db/services/dialog_service.py": "22be233dd35f50af41b406104e8a046363296c6327bf0e97d6e438121f9d842b",
    "rag/advanced_rag/agentic_rag.py": "75fd5ee92387f7c44f063ee332b6d355622c3ff27b69c79a2e5dd95233138b23",
    "agent/component/agent_with_tools.py": "181fdb3f2307be50ef18a031b75bcefb4403dc8d706bada63843bd07f480998e",
}
POST = {
    "rag/nlp/search.py": "5c96ad4364907378b4d579e5a0ec74be3b627f2616c96681198b6bcf1853534d",
    "api/db/services/dialog_service.py": "1c74b3d71a3778790c25b026ff00d69bedba96aea941ebb373fb2243e6425738",
    "rag/advanced_rag/agentic_rag.py": "9a4d6b951c064060be3b504b35bd34babe56ffd47346a88384a384d172b5a5ac",
    "agent/component/agent_with_tools.py": "096520e7820b1412ea2d2707542d3ef9767d4b02d65cf5ac31e2f5d1b2469e63",
}

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main() -> None:
    ap=argparse.ArgumentParser(); ap.add_argument("root", type=Path); ap.add_argument("--mode", choices=["prepatch","postpatch"], required=True); args=ap.parse_args()
    expected = PRE if args.mode == "prepatch" else POST
    failed=[]
    for rel,want in expected.items():
        p=args.root/rel
        got=sha(p) if p.exists() else "MISSING"
        if got != want: failed.append((rel,want,got))
    if failed:
        for rel,want,got in failed: print(f"FAIL {rel}\n  expected={want}\n  got={got}")
        raise SystemExit(2)
    print(f"runtime source hash verification: PASS ({args.mode})")
if __name__ == "__main__": main()
