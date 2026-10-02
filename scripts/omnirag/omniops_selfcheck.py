#!/usr/bin/env python3
"""End-to-end HTTP self-check for OmniOps through the FastAPI gateway."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def req(url: str, body: dict | None = None, headers: dict[str, str] | None = None) -> dict:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="GET" if body is None else "POST")
    if data is not None:
        request.add_header("Content-Type", "application/json")
    for key, value in (headers or {}).items():
        request.add_header(key, value)
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_job(base: str, run_id: str) -> dict:
    for _ in range(80):
        value = req(f"{base}/api/v1/analyses/{run_id}")
        if value["state"] in {"completed", "failed"}:
            return value
        time.sleep(0.1)
    raise RuntimeError("analysis job timed out")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=18090)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="omniops-selfcheck-") as temp:
        env = os.environ.copy()
        env.update({"OMNIOPS_MODE": "demo", "OMNIOPS_PORT": str(args.port), "OMNIAI_GATEWAY_PORT": str(args.port), "OMNIOPS_DATA_ROOT": temp, "PYTHONPATH": str(ROOT)})
        proc = subprocess.Popen([sys.executable, str(ROOT / "scripts/omnirag/run_omniops.py"), "--host", "127.0.0.1", "--port", str(args.port)], cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        base = f"http://127.0.0.1:{args.port}"
        try:
            for _ in range(60):
                try:
                    health = req(base + "/api/v1/health")
                    break
                except Exception:
                    time.sleep(0.1)
            else:
                output = proc.stdout.read() if proc.stdout else ""
                raise RuntimeError(f"server did not start: {output}")
            overview = req(base + "/api/v1/overview")
            submitted = req(base + "/api/v1/analyses", {"incident_id": "INC-20260922-001"}, {"Idempotency-Key": "selfcheck-gw01"})
            job = wait_job(base, submitted["run_id"])
            analysis = job["result"]
            traces = req(base + "/api/v1/traces?incident_id=INC-20260922-001")
            evaluation = req(base + "/api/v1/evaluation")
            modules = req(base + "/api/v1/platform/modules")
            assert health["ok"] is True
            assert health["gateway"]["framework"] == "FastAPI"
            assert overview["incidents_total"] >= 3
            assert analysis["decision"] in {"pass", "retrieve_more", "abstain"}
            assert analysis["mode"] == "demo"
            assert analysis["citations"]
            assert traces["items"] and traces["items"][0]["steps"]
            assert any(x["status"] == "not_run" for x in evaluation["items"])
            assert any(x["id"] == "langgraph" for x in modules["items"])
            print("OmniOps FastAPI HTTP self-check: PASS")
            print(f"decision={analysis['decision']} confidence={analysis['confidence']:.4f} trace_steps={len(traces['items'][0]['steps'])}")
            return 0
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
