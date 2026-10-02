"""Exercise the FastAPI edge contract over a real localhost socket."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
PORT = 18101
BASE = f"http://127.0.0.1:{PORT}"


def main() -> None:
    log_dir = ROOT / "artifacts/runtime/fastapi"
    log_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="omniai-gateway-contract-") as data_root, (log_dir / "server.log").open("w", encoding="utf-8") as log:
        env = {**os.environ, "PYTHONPATH": str(ROOT), "OMNIOPS_MODE": "demo", "OMNIOPS_DATA_ROOT": data_root}
        proc = subprocess.Popen([sys.executable, "scripts/omnirag/run_omniops.py", "--host", "127.0.0.1", "--port", str(PORT)], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            with httpx.Client(base_url=BASE, timeout=8) as client:
                for _ in range(80):
                    if proc.poll() is not None:
                        raise RuntimeError("Gateway exited during startup")
                    try:
                        if client.get("/api/v1/health").status_code == 200:
                            break
                    except httpx.ConnectError:
                        time.sleep(0.1)
                else:
                    raise TimeoutError("Gateway did not become healthy")
                paths = ("/api/v1/health", "/api/v1/platform/modules", "/docs", "/openapi.json", "/metrics")
                statuses = {path: client.get(path).status_code for path in paths}
                assert all(code == 200 for code in statuses.values()), statuses
                health = client.get("/api/v1/health")
                assert health.headers["x-request-id"] and health.json()["version"] == "2.0.0"
                unknown = client.get("/api/v1/incidents/UNKNOWN", headers={"X-Request-ID": "gateway-smoke"})
                assert unknown.status_code == 404 and unknown.json()["error"]["request_id"] == "gateway-smoke"
                body = {"incident_id": "INC-20260922-001", "question": "分析 GW-01 DNS 异常"}
                first = client.post("/api/v1/analyses", json=body, headers={"Idempotency-Key": "gateway-contract-smoke"})
                again = client.post("/api/v1/analyses", json=body, headers={"Idempotency-Key": "gateway-contract-smoke"})
                assert first.status_code == again.status_code == 202
                run_id = first.json()["run_id"]
                assert again.json()["run_id"] == run_id
                for _ in range(80):
                    job = client.get(f"/api/v1/analyses/{run_id}").json()
                    if job["state"] in {"completed", "failed"}:
                        break
                    time.sleep(0.1)
                assert job["state"] == "completed", job
                events = client.get(f"/api/v1/analyses/{run_id}/events")
                assert events.status_code == 200 and "event: analysis" in events.text
                metrics = client.get("/metrics").text
                assert "omniai_http_requests_total" in metrics
                print(json.dumps({"status": statuses, "request_id": "PASS", "error_model": "PASS", "idempotency": "PASS", "async_202": "PASS", "sse": "PASS", "metrics": "PASS", "run_id": run_id}))
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)


if __name__ == "__main__":
    main()
