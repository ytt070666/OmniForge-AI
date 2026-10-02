"""Verify real MCP discovery and tool execution over streamable HTTP."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

ROOT = Path(__file__).resolve().parents[2]
PORT = 18098


async def check() -> None:
    async with streamable_http_client(f"http://127.0.0.1:{PORT}/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = {item.name for item in tools.tools}
            assert names == {"lookup_device", "search_runbook", "calculate_availability"}, names
            assert all(item.inputSchema for item in tools.tools)
            device = await session.call_tool("lookup_device", {"device_id": "GW-01"})
            runbook = await session.call_tool("search_runbook", {"query": "gateway"})
            availability = await session.call_tool("calculate_availability", {"total_minutes": 100, "downtime_minutes": 1})
            assert not device.isError and "GW-01" in str(device.content)
            assert not runbook.isError and "gateway" in str(runbook.content)
            assert not availability.isError and "99" in str(availability.content)
            print(json.dumps({"tools": sorted(names), "lookup_device": "PASS", "search_runbook": "PASS", "calculate_availability": "PASS"}))


def main() -> None:
    log_dir = ROOT / "artifacts/runtime/integration/mcp"
    log_dir.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    with (log_dir / "server.log").open("w", encoding="utf-8") as log:
        proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "scripts.omniai.mcp_app:app", "--host", "127.0.0.1", "--port", str(PORT)], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            for _ in range(30):
                if proc.poll() is not None:
                    raise RuntimeError("MCP server exited during startup")
                try:
                    asyncio.run(check())
                    return
                except OSError:
                    time.sleep(0.2)
            raise TimeoutError("MCP server did not accept connections")
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)


if __name__ == "__main__":
    main()
