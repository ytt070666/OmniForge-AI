"""Check NATS -> Go realtime gateway -> SSE over local TCP."""

from __future__ import annotations

import asyncio
import argparse
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import nats

ROOT = Path(__file__).resolve().parents[2]
PORT = 18099
BASE = f"http://127.0.0.1:{PORT}"


async def publish() -> None:
    nc = await nats.connect("nats://127.0.0.1:4222")
    event = {"type": "analysis.completed", "trace_id": "smoke-go-sse", "payload": {"run_id": "SMOKE-1"}}
    await nc.publish("omniai.analysis.completed", json.dumps(event).encode("utf-8"))
    await nc.flush()
    await nc.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--idle-seconds", type=float, default=0.2)
    args = parser.parse_args()
    log_dir = ROOT / "artifacts/runtime/go"
    log_dir.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "OMNIAI_NATS_URL": "nats://127.0.0.1:4222", "OMNIAI_REALTIME_ADDR": f"127.0.0.1:{PORT}"}
    with (log_dir / "server.log").open("w", encoding="utf-8") as log:
        proc = subprocess.Popen([str(ROOT / "services/omniai_realtime_go/realtime.exe")], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            for _ in range(60):
                if proc.poll() is not None:
                    raise RuntimeError("Go gateway exited during startup")
                try:
                    with urllib.request.urlopen(BASE + "/health", timeout=1) as response:
                        health = json.load(response)
                    break
                except OSError:
                    time.sleep(0.1)
            else:
                raise TimeoutError("Go gateway did not become healthy")
            assert health["ok"] and health["nats"], health
            try:
                urllib.request.urlopen(urllib.request.Request(BASE + "/publish", data=b"not-json", method="POST"), timeout=3)
                raise AssertionError("invalid JSON must return 400")
            except urllib.error.HTTPError as exc:
                assert exc.code == 400 and json.load(exc)["error"]["code"] == "INVALID_JSON"
            with urllib.request.urlopen(BASE + "/events", timeout=max(8, args.idle_seconds + 5)) as response:
                time.sleep(args.idle_seconds)
                asyncio.run(publish())
                event_type = ""
                while event_type != "event: omniai":
                    event_type = response.readline().decode("utf-8").strip()
                payload = response.readline().decode("utf-8").strip()
            assert event_type == "event: omniai", event_type
            assert "smoke-go-sse" in payload, payload
            print(json.dumps({"go_health": health, "sse_event": event_type, "nats_trace": "smoke-go-sse", "idle_seconds": args.idle_seconds}))
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)


if __name__ == "__main__":
    main()
