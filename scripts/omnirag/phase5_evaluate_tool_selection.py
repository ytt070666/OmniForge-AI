#!/usr/bin/env python3
"""Offline smoke benchmark for the deterministic Phase-5 tool pre-selector.

This benchmark measures only shortlist routing on a synthetic capability catalog.
It is not an end-to-end Agent/tool-success result and must not be reported as one.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from extensions.omnirag.tools.policy import ToolPolicy
from extensions.omnirag.tools.registry import ToolRegistry
from extensions.omnirag.tools.selector import ToolSelectorV1
from extensions.omnirag.tools.types import ToolDescriptor, ToolRisk, ToolSource

CASES = ROOT / "benchmarks" / "omnirag" / "phase5" / "tool_selection_cases.jsonl"


def registry() -> ToolRegistry:
    schema = {"type": "object", "properties": {"query": {"type": "string"}}}
    rows = [
        ToolDescriptor("search_docs_0", "search_docs", "Search, find, retrieve and query enterprise knowledge-base documents; 搜索、检索、查找企业知识库文档", schema, ToolSource.BUILTIN, risk=ToolRisk.READ),
        ToolDescriptor("weather_1", "weather_forecast", "Get weather forecast, temperature and rain conditions; 查询天气、气温和天气预报", schema, ToolSource.BUILTIN, risk=ToolRisk.READ),
        ToolDescriptor("lookup_device_2", "lookup_device", "Look up device or asset catalog records by device ID; 查询设备和资产目录信息", schema, ToolSource.MCP, source_id="reference", risk=ToolRisk.READ, read_only=True),
        ToolDescriptor("search_runbook_3", "search_runbook", "Search operational runbooks for troubleshooting and incident procedures; 搜索故障排查手册和运行手册", schema, ToolSource.MCP, source_id="reference", risk=ToolRisk.READ, read_only=True),
        ToolDescriptor("availability_4", "calculate_availability", "Calculate service availability from total minutes and downtime minutes; 根据总时长与停机时长计算可用率", schema, ToolSource.MCP, source_id="reference", risk=ToolRisk.READ, read_only=True),
    ]
    return ToolRegistry(rows)


def main() -> int:
    cases = [json.loads(x) for x in CASES.read_text(encoding="utf-8").splitlines() if x.strip()]
    selector = ToolSelectorV1()
    reg = registry()
    policy = ToolPolicy(max_visible_tools=3, selector_min_score=0.01)
    top1 = 0
    top3 = 0
    rows = []
    for case in cases:
        out = selector.select(case["query"], reg, policy)
        selected = list(out.selected_names)
        expected = case["expected"]
        top1 += bool(selected and selected[0] == expected)
        top3 += expected in selected[:3]
        rows.append({"query": case["query"], "expected": expected, "selected": selected, "scores": out.scores})
    n = len(cases)
    report = {"cases": n, "top1": top1 / n if n else 0.0, "top3": top3 / n if n else 0.0, "rows": rows}
    out_path = ROOT / "artifacts" / "omnirag" / "phase5_tool_selection_smoke.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("cases", "top1", "top3")}, ensure_ascii=False))
    print(f"wrote {out_path.relative_to(ROOT)}")
    return 0 if report["top3"] == 1.0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
