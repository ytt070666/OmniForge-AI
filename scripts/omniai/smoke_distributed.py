"""Run a local Gateway -> NATS -> Agent worker -> Gateway smoke test."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PORT = 18094
BASE = f"http://127.0.0.1:{PORT}"
GATEWAY_PYTHON = ROOT / ".venv-gateway/Scripts/python.exe"
AGENT_PYTHON = ROOT / ".venv-agent/Scripts/python.exe"


def request(path: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=data)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=8) as response:
        return json.load(response)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="omniai-nats-") as data_root:
        env = os.environ.copy()
        env.update({
            "PYTHONPATH": str(ROOT), "OMNIOPS_MODE": "demo",
            "OMNIOPS_DATA_ROOT": data_root, "OMNIAI_JOB_BACKEND": "nats",
            "OMNIAI_NATS_URL": "nats://127.0.0.1:4222",
        })
        log_dir = ROOT / "artifacts/runtime/nats"
        log_dir.mkdir(parents=True, exist_ok=True)
        with (log_dir / "gateway.log").open("w", encoding="utf-8") as gateway_log, (log_dir / "worker.log").open("w", encoding="utf-8") as worker_log:
            gateway = subprocess.Popen(
                [str(GATEWAY_PYTHON), "scripts/omnirag/run_omniops.py", "--host", "127.0.0.1", "--port", str(PORT)],
                cwd=ROOT, env=env, stdout=gateway_log, stderr=subprocess.STDOUT,
            )
            worker = None
            try:
                for _ in range(100):
                    if gateway.poll() is not None:
                        raise RuntimeError("Gateway exited during startup")
                    try:
                        request("/api/v1/health")
                        break
                    except OSError:
                        time.sleep(0.1)
                else:
                    raise TimeoutError("Gateway did not become healthy")
                worker = subprocess.Popen(
                    [str(AGENT_PYTHON), "-m", "services.omniai_agent.worker"],
                    cwd=ROOT, env=env, stdout=worker_log, stderr=subprocess.STDOUT,
                )
                time.sleep(2)
                if worker.poll() is not None:
                    raise RuntimeError("Agent worker exited during startup")
                submitted = request("/api/v1/analyses", {"incident_id": "INC-20260922-001", "question": "分析 GW-01 DNS 异常，并给出有证据的结论。"})
                for _ in range(100):
                    result = request(f"/api/v1/analyses/{submitted['run_id']}")
                    if result["state"] in {"completed", "failed"}:
                        break
                    time.sleep(0.1)
                else:
                    raise TimeoutError("NATS job did not finish")
                assert result["state"] == "completed", result
                assert result["result"]["verification"]["decision"] == "pass", result
                print(json.dumps({"integration_mode": "deterministic_product", "backend": "nats", "run_id": result["run_id"], "state": result["state"], "decision": result["result"]["decision"]}, ensure_ascii=False))
            finally:
                for proc in (worker, gateway):
                    if proc is not None:
                        proc.terminate()
                        try:
                            proc.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                            proc.wait(timeout=5)


if __name__ == "__main__":
    main()
