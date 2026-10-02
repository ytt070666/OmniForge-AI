"""Run bounded 10/25/50-client Locust checks against a temporary gateway."""

from __future__ import annotations

import csv
import json
import os
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts/runtime/loadtest"
PORT = 18100


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    locust = ROOT / ".venv-load/Scripts/locust.exe"
    gateway_python = ROOT / ".venv-gateway/Scripts/python.exe"
    summaries = []
    for users in (10, 25, 50):
        with tempfile.TemporaryDirectory(prefix=f"omniai-load-{users}-") as data_root:
            env = {**os.environ, "PYTHONPATH": str(ROOT), "PYTHONUTF8": "1", "OMNIOPS_MODE": "demo", "OMNIOPS_DATA_ROOT": data_root}
            with (OUT / f"gateway_{users}.log").open("w", encoding="utf-8") as gateway_log:
                gateway = subprocess.Popen([str(gateway_python), "scripts/omnirag/run_omniops.py", "--host", "127.0.0.1", "--port", str(PORT)], cwd=ROOT, env=env, stdout=gateway_log, stderr=subprocess.STDOUT)
                try:
                    for _ in range(80):
                        if gateway.poll() is not None:
                            raise RuntimeError("Gateway exited during startup")
                        try:
                            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/v1/health", timeout=2):
                                break
                        except OSError:
                            time.sleep(0.1)
                    else:
                        raise TimeoutError("Gateway did not become healthy")
                    prefix = OUT / f"locust_{users}"
                    with (OUT / f"locust_{users}.log").open("w", encoding="utf-8") as log:
                        run = subprocess.run([str(locust), "-f", "benchmarks/omniai/load/locustfile.py", "--headless", "-u", str(users), "-r", str(users), "-t", "8s", "--host", f"http://127.0.0.1:{PORT}", "--csv", str(prefix)], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=30)
                finally:
                    gateway.terminate()
                    try:
                        gateway.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        gateway.kill()
                        gateway.wait(timeout=5)
            with (OUT / f"locust_{users}_stats.csv").open(newline="", encoding="utf-8") as csvfile:
                aggregate = next(row for row in csv.DictReader(csvfile) if row["Name"] == "Aggregated")
            summaries.append({"users": users, "locust_exit": run.returncode, "requests": int(aggregate["Request Count"]), "failures": int(aggregate["Failure Count"]), "rps": float(aggregate["Requests/s"]), "p50_ms": aggregate["50%"], "p95_ms": aggregate["95%"], "p99_ms": aggregate["99%"]})
    (OUT / "summary.json").write_text(json.dumps({"type": "LOCAL DEVELOPMENT LOAD TEST", "results": summaries}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summaries, ensure_ascii=False))


if __name__ == "__main__":
    main()
