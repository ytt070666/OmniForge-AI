#!/usr/bin/env python3
"""Deterministic offline Phase-5 contract checks."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from extensions.omnirag.dsl import TaskSpec, TaskSpecValidationError, compile_taskspec, validate_taskspec
from extensions.omnirag.mcp.reference_server import calculate_availability, lookup_device
from extensions.omnirag.tools.policy import ToolPolicy
from extensions.omnirag.tools.registry import ToolRegistry
from extensions.omnirag.tools.session import GovernedToolCallSession
from extensions.omnirag.tools.types import ToolDescriptor, ToolRisk, ToolSource


class BaseSession:
    def __init__(self):
        self.calls = 0

    async def tool_call_async(self, name, arguments, request_timeout=None):
        self.calls += 1
        return {"name": name, "arguments": arguments}


def registry() -> ToolRegistry:
    read_schema = {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
    code_schema = {"type": "object", "properties": {"script": {"type": "string"}}, "required": ["script"]}
    return ToolRegistry(
        [
            ToolDescriptor("search_0", "search", "Search documents", read_schema, ToolSource.BUILTIN, risk=ToolRisk.READ),
            ToolDescriptor("code_1", "execute_code", "Execute code", code_schema, ToolSource.BUILTIN, risk=ToolRisk.EXECUTE),
        ]
    )


async def main() -> int:
    checks = 0
    reg = registry()
    default_policy = ToolPolicy()
    assert default_policy.permits(reg.get("search_0"))[0] is True
    assert default_policy.permits(reg.get("code_1"))[0] is False
    checks += 2

    base = BaseSession()
    session = GovernedToolCallSession(base, reg, ("search_0",), ToolPolicy(max_total_calls=1, max_calls_per_tool=1))
    await session.tool_call_async("search_0", {"query": "contract"})
    assert base.calls == 1
    assert session.trace_snapshot()[0]["argument_keys"] == ["query"]
    assert "contract" not in json.dumps(session.trace_snapshot())
    checks += 3

    try:
        await session.tool_call_async("search_0", {"query": "second"})
        raise AssertionError("budget check did not fire")
    except RuntimeError:
        checks += 1

    raw = json.loads((ROOT / "benchmarks/omnirag/phase5/taskspec_grounded_qa.json").read_text(encoding="utf-8"))
    compiled = compile_taskspec(validate_taskspec(TaskSpec.from_dict(raw)))
    assert compiled["components"]["Agent:Omni_answer"]["upstream"] == ["Retrieval:Omni_retrieve"]
    assert compiled["components"]["Message:Omni_respond"]["downstream"] == []
    checks += 2

    unsafe = TaskSpec.from_dict(
        {
            "version": "1.0",
            "name": "unsafe",
            "steps": [
                {"id": "a", "kind": "agent", "params": {"llm_id": "x", "token": "secret"}},
                {"id": "m", "kind": "message", "depends_on": ["a"], "params": {"content": ["${a.content}"]}},
            ],
        }
    )
    try:
        validate_taskspec(unsafe)
        raise AssertionError("secret-like field was accepted")
    except TaskSpecValidationError:
        checks += 1

    assert lookup_device("GW-01")["found"] is True
    assert calculate_availability(100, 1)["availability_percent"] == 99.0
    checks += 2

    print(f"Phase-5 contract checks: PASS ({checks} assertions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
