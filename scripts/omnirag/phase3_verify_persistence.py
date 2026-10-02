#!/usr/bin/env python3
"""Re-read Phase-3 sessions after RAGFlow restart and compare verifier decisions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.omnirag.phase1_collect_baseline import RagflowClient


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--auth-file", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--api-root", default="http://127.0.0.1:9380/api/v1")
    args = parser.parse_args()
    auth = json.loads(args.auth_file.read_text(encoding="utf-8-sig"))
    client = RagflowClient(args.api_root, auth["api_key"])
    rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    latest = {row["query_id"]: row for row in rows if row.get("completed")}
    outcomes = []
    for query_id, row in sorted(latest.items()):
        session = client.get(f"chats/{row['chat_id']}/sessions/{row['session_id']}")["data"] or {}
        reference = (session.get("reference") or [{}])[-1]
        actual = reference.get("omnirag_verification") if isinstance(reference, dict) else None
        matching = actual == row.get("verification") and bool(actual and actual.get("enabled"))
        outcomes.append({"query_id": query_id, "session_id": row["session_id"], "matching": matching,
                         "decision": actual.get("decision") if actual else None})
        print(f"{query_id}: {'PASS' if matching else 'FAIL'}")
    passed = len(outcomes) == 18 and all(item["matching"] for item in outcomes)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"status": "PASS" if passed else "FAIL", "sessions": outcomes}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
