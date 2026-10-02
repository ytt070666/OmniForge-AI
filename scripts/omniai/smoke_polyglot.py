"""Check the built NestJS and Spring services over real local HTTP."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT / "artifacts/runtime/integration"
GATEWAY_PORT, BFF_PORT, SPRING_PORT = 18095, 18096, 18097


def get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.load(response)


def wait(url: str, process: subprocess.Popen) -> dict:
    for _ in range(120):
        if process.poll() is not None:
            raise RuntimeError(f"process exited before {url} became healthy")
        try:
            return get(url)
        except OSError:
            time.sleep(0.2)
    raise TimeoutError(url)


def main() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    processes = []
    handles = []
    with tempfile.TemporaryDirectory(prefix="omniai-polyglot-") as data_root:
        env = os.environ.copy()
        env.update({"PYTHONPATH": str(ROOT), "OMNIOPS_MODE": "demo", "OMNIOPS_DATA_ROOT": data_root})

        def launch(name: str, argv: list[str], extra: dict[str, str]) -> subprocess.Popen:
            handle = (LOG_DIR / f"{name}.log").open("w", encoding="utf-8")
            handles.append(handle)
            proc = subprocess.Popen(argv, cwd=ROOT, env={**env, **extra}, stdout=handle, stderr=subprocess.STDOUT)
            processes.append(proc)
            return proc

        try:
            gateway = launch("gateway", [str(ROOT / ".venv-gateway/Scripts/python.exe"), "scripts/omnirag/run_omniops.py", "--host", "127.0.0.1", "--port", str(GATEWAY_PORT)], {})
            gw_health = wait(f"http://127.0.0.1:{GATEWAY_PORT}/api/v1/health", gateway)
            bff = launch("bff", ["node", "services/omniai_bff_nest/dist/main.js"], {"PORT": str(BFF_PORT), "OMNIAI_GATEWAY_URL": f"http://127.0.0.1:{GATEWAY_PORT}"})
            bff_health = wait(f"http://127.0.0.1:{BFF_PORT}/health", bff)
            summary = get(f"http://127.0.0.1:{BFF_PORT}/api/v1/platform/summary")
            spring = launch("spring", ["java", "-jar", "services/omniai_enterprise_spring/target/enterprise-connector-0.1.0.jar"], {"SERVER_PORT": str(SPRING_PORT)})
            spring_health = wait(f"http://127.0.0.1:{SPRING_PORT}/actuator/health", spring)
            spring_contract = get(f"http://127.0.0.1:{SPRING_PORT}/api/v1/health")
            asset = get(f"http://127.0.0.1:{SPRING_PORT}/api/v1/assets/GW-01")
            assert gw_health["ok"] and gw_health["service"] == "omniai-gateway"
            assert bff_health["service"] == "omniai-bff-nest" and summary["health"]["ok"]
            assert any(x["id"] == "langgraph" for x in summary["modules"]["items"])
            assert spring_health["status"] == "UP" and asset["id"] == "GW-01"
            assert spring_contract["service"] == "omniai-enterprise-spring"
            try:
                get(f"http://127.0.0.1:{SPRING_PORT}/api/v1/assets/UNKNOWN")
                raise AssertionError("unknown asset must return 404")
            except urllib.error.HTTPError as exc:
                assert exc.code == 404 and json.load(exc)["error"]["code"] == "ASSET_NOT_FOUND"
            print(json.dumps({"nestjs_gateway": "PASS", "spring_health": spring_health["status"], "asset": asset}, ensure_ascii=False))
        finally:
            for proc in reversed(processes):
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
            for handle in handles:
                handle.close()


if __name__ == "__main__":
    main()
