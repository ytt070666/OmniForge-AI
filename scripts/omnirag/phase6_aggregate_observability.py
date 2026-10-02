#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from extensions.omnirag.observability.metrics import aggregate


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--events", required=True)
    p.add_argument("--price-table", default=None)
    p.add_argument("--output", default=None)
    args = p.parse_args()
    prices = None
    if args.price_table:
        prices = json.loads((ROOT / args.price_table).read_text(encoding="utf-8"))
    report = aggregate(read_jsonl(ROOT / args.events), price_table=prices)
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    print(text)
    if args.output:
        path = ROOT / args.output
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
