#!/usr/bin/env python3
"""Validate and compile OmniRAG TaskSpec v1.0 to RAGFlow Canvas DSL."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from extensions.omnirag.dsl import TaskSpec, compile_taskspec, validate_taskspec


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="TaskSpec JSON file")
    parser.add_argument("--output", help="Compiled RAGFlow DSL JSON; stdout if omitted")
    args = parser.parse_args()

    source = Path(args.input)
    raw = json.loads(source.read_text(encoding="utf-8"))
    spec = validate_taskspec(TaskSpec.from_dict(raw))
    compiled = compile_taskspec(spec)
    text = json.dumps(compiled, ensure_ascii=False, indent=2)
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
        print(f"TaskSpec compile: PASS -> {out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
