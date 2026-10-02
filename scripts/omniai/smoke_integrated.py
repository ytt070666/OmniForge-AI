"""Exercise the deterministic OmniOps product through live modular HTTP services."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
from contextlib import ExitStack
from pathlib import Path

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts/runtime/integration"
GATEWAY = "http://127.0.0.1:18111"
AGENT = "http://127.0.0.1:18112"
MCP = "http://127.0.0.1:18113/mcp"
INCIDENT = "INC-20260922-001"


def wait_health(client: httpx.Client, path: str, proc: subprocess.Popen) -> None:
    for _ in range(100):
        if proc.poll() is not None:
            raise RuntimeError(f"service exited before {path} became healthy")
        try:
            if client.get(path).status_code == 200:
                return
        except httpx.ConnectError:
            pass
        time.sleep(0.1)
    raise TimeoutError(f"service did not become healthy: {path}")


async def mcp_lookup() -> dict:
    async with streamable_http_client(MCP) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            names = {item.name for item in (await session.list_tools()).tools}
            assert "lookup_device" in names
            result = await session.call_tool("lookup_device", {"device_id": "GW-01"})
            assert not result.isError and "GW-01" in str(result.content)
            return {"lookup_device": "PASS", "tool_count": len(names)}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="omniai-integrated-") as data_root, ExitStack() as stack:
        agent_log = stack.enter_context((OUT / "integrated_agent.log").open("w", encoding="utf-8"))
        gateway_log = stack.enter_context((OUT / "integrated_gateway.log").open("w", encoding="utf-8"))
        mcp_log = stack.enter_context((OUT / "integrated_mcp.log").open("w", encoding="utf-8"))
        env = {**os.environ, "PYTHONPATH": str(ROOT), "OMNIOPS_MODE": "demo", "OMNIOPS_DATA_ROOT": data_root}
        agent = subprocess.Popen([sys.executable, "-m", "uvicorn", "services.omniai_agent.app:app", "--host", "127.0.0.1", "--port", "18112"], cwd=ROOT, env=env, stdout=agent_log, stderr=subprocess.STDOUT)
        mcp = subprocess.Popen([sys.executable, "-m", "uvicorn", "scripts.omniai.mcp_app:app", "--host", "127.0.0.1", "--port", "18113"], cwd=ROOT, env=env, stdout=mcp_log, stderr=subprocess.STDOUT)
        gateway_env = {**env, "OMNIAI_AGENT_URL": AGENT}
        gateway_python = ROOT / ".venv-gateway/Scripts/python.exe"
        gateway = subprocess.Popen([str(gateway_python), "scripts/omnirag/run_omniops.py", "--host", "127.0.0.1", "--port", "18111"], cwd=ROOT, env=gateway_env, stdout=gateway_log, stderr=subprocess.STDOUT)
        try:
            with httpx.Client(base_url=AGENT, timeout=15) as agent_client, httpx.Client(base_url=GATEWAY, timeout=30) as client:
                wait_health(agent_client, "/health", agent)
                wait_health(client, "/api/v1/health", gateway)
                assert client.get("/").status_code == 200
                incident = client.get(f"/api/v1/incidents/{INCIDENT}")
                assert incident.status_code == 200 and incident.json()["asset_id"] == "GW-01"
                request_id = "integrated-gw01"
                graph = client.post("/api/v1/agent/run", json={"incident_id": INCIDENT, "query": "Analyze GW-01 DNS anomaly with evidence", "max_retries": 1}, headers={"X-Request-ID": request_id})
                assert graph.status_code == 200, graph.text
                state = graph.json()
                assert graph.headers["X-Request-ID"] == request_id
                assert state["decision"] == "pass" and state["verification"]["decision"] == "pass"
                assert any(item["id"] == "EV-001" for item in state["evidence"])
                assert any(item["tool"] == "lookup_device" and item["risk"] == "read" for item in state["tool_results"])
                mcp_result = asyncio.run(mcp_lookup())
                submission = client.post("/api/v1/analyses", json={"incident_id": INCIDENT, "question": "Analyze GW-01 DNS anomaly"}, headers={"Idempotency-Key": "integrated-gw01"})
                assert submission.status_code == 202
                run_id = submission.json()["run_id"]
                for _ in range(100):
                    job = client.get(f"/api/v1/analyses/{run_id}").json()
                    if job["state"] in {"completed", "failed"}:
                        break
                    time.sleep(0.1)
                assert job["state"] == "completed" and job["result"]["decision"] == "pass", job
                assert job["result"]["citations"]
                events = client.get(f"/api/v1/analyses/{run_id}/events")
                assert events.status_code == 200 and "event: analysis" in events.text
                traces = client.get("/api/v1/traces", params={"incident_id": INCIDENT}).json()["items"]
                assert traces and traces[0]["steps"]
                evidence = client.get("/api/v1/evidence", params={"incident_id": INCIDENT}).json()["items"]
                assert len(evidence) >= 4
                result = {"integration_mode": "deterministic_product", "gateway_to_langgraph": "PASS", "request_id": request_id, "incident_id": INCIDENT, "graph_decision": state["decision"], "graph_evidence": len(state["evidence"]), "graph_tool": "lookup_device", "mcp": mcp_result, "job_run_id": run_id, "job_state": job["state"], "job_decision": job["result"]["decision"], "citations": len(job["result"]["citations"]), "trace_steps": len(traces[0]["steps"]), "sse": "PASS", "ui_http": 200}
                (OUT / "integrated_smoke.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                print(json.dumps(result, ensure_ascii=False))
        finally:
            for proc in (gateway, agent, mcp):
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)


if __name__ == "__main__":
    main()
