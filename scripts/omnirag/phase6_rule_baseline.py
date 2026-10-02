#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from extensions.omnirag.training.baseline_router import predict
from extensions.omnirag.training.dataset import load_jsonl, write_jsonl


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", default="benchmarks/omnirag/phase6/router/protected_benchmark.jsonl")
    p.add_argument("--output", default="artifacts/omnirag/phase6/rule_baseline_protected_predictions.jsonl")
    args = p.parse_args()
    rows = load_jsonl(ROOT / args.dataset)
    preds = [{"id": row["id"], "prediction": predict(row["query"])} for row in rows]
    write_jsonl(ROOT / args.output, preds)
    print(f"Wrote {len(preds)} deterministic baseline predictions to {args.output}")


if __name__ == "__main__":
    main()
