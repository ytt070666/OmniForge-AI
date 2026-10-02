#!/usr/bin/env python3
"""Runtime-only Phase-5 contracts to run after the full RAGFlow environment exists.

This script is deliberately NOT part of the pre-local PASS claim. It imports
RAGFlow's real Canvas/component stack and the external MCP SDK, so it belongs to
the later local acceptance stage after ``uv sync`` / container dependencies.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--taskspec",
        default=str(ROOT / "benchmarks/omnirag/phase5/taskspec_grounded_qa.json"),
        help="TaskSpec fixture to compile and validate against native Canvas parameter classes",
    )
    args = parser.parse_args()

    from agent.canvas import Graph
    from extensions.omnirag.dsl import TaskSpec, compile_taskspec, validate_taskspec
    from extensions.omnirag.mcp.reference_server import build_server

    raw = json.loads(Path(args.taskspec).read_text(encoding="utf-8"))
    compiled = compile_taskspec(validate_taskspec(TaskSpec.from_dict(raw)))
    params = Graph.validate_component_parameters(compiled)
    expected = set(compiled["components"])
    if set(params) != expected:
        raise AssertionError(f"native Graph parameter validation returned {set(params)}; expected {expected}")

    # Construction exercises the installed MCP SDK decorator/API contract. It
    # does not open a socket and therefore remains safe for a contract check.
    server = build_server()
    if server is None:
        raise AssertionError("reference MCP server construction returned None")

    print(f"Phase-5 runtime contracts: PASS ({len(params)} native Canvas components + MCP server construction)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
