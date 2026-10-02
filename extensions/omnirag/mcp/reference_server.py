"""Small read-only MCP server for local integration tests and demonstrations.

RAGFlow already implements MCP client/server transport. This module exists only
as a deterministic external server that OmniRAG can connect to during Phase-5
acceptance tests. It deliberately contains no write/destructive tools.
"""

from __future__ import annotations

from typing import Any

_DEVICE_CATALOG = {
    "GW-01": {"role": "edge-gateway", "site": "lab-a", "owner": "platform", "status": "active"},
    "SENSOR-17": {"role": "temperature-sensor", "site": "lab-a", "owner": "iot", "status": "active"},
    "DB-02": {"role": "analytics-database", "site": "dc-1", "owner": "data", "status": "maintenance"},
}

_RUNBOOKS = {
    "gateway": "If an edge gateway stops reporting, verify power, local link state, DNS resolution, and the upstream broker before restarting it.",
    "database": "For analytics database maintenance, confirm the maintenance window, replica health, backups, and read-only traffic routing before intervention.",
}


def lookup_device(device_id: str) -> dict[str, Any]:
    key = (device_id or "").strip().upper()
    row = _DEVICE_CATALOG.get(key)
    return {"found": bool(row), "device_id": key, "record": dict(row or {})}


def search_runbook(query: str) -> list[dict[str, str]]:
    q = (query or "").lower()
    rows = []
    for name, text in _RUNBOOKS.items():
        if name in q or any(token in text.lower() for token in q.split() if len(token) > 3):
            rows.append({"name": name, "text": text})
    return rows


def calculate_availability(total_minutes: float, downtime_minutes: float) -> dict[str, float]:
    total = float(total_minutes)
    down = float(downtime_minutes)
    if total <= 0:
        raise ValueError("total_minutes must be greater than zero")
    if down < 0 or down > total:
        raise ValueError("downtime_minutes must be between zero and total_minutes")
    availability = (total - down) / total
    return {"availability": round(availability, 8), "availability_percent": round(availability * 100, 6)}


def build_server():
    # Imported lazily so static tests do not require the project virtualenv.
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("OmniRAG Reference Read-Only Tools")
    mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True})(lookup_device)
    mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False})(search_runbook)
    mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False})(calculate_availability)
    return mcp


def main() -> None:
    server = build_server()
    server.run(transport="streamable-http")


if __name__ == "__main__":
    main()
