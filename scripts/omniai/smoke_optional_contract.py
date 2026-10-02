"""Check the shared HTTP envelope for one optional FastAPI service."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from omniai_platform.http_contract import install_http_contract

ROUTES = {
    "agent": ("services.omniai_agent.app", "/api/v1/agent/run"),
    "llamaindex": ("services.omniai_llamaindex.app", "/api/v1/index"),
    "tensorflow": ("services.omniai_tensorflow.app", "/api/v1/severity"),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("service", choices=ROUTES)
    args = parser.parse_args()
    module, route = ROUTES[args.service]
    app = importlib.import_module(module).app
    client = TestClient(app)
    request_id = f"contract-{args.service}"
    health = client.get("/health", headers={"X-Request-ID": request_id})
    assert health.status_code == 200
    assert health.headers["X-Request-ID"] == request_id
    assert health.json()["service"] and health.json()["version"]
    invalid = client.post(route, json={}, headers={"X-Request-ID": request_id})
    assert invalid.status_code == 422
    assert invalid.json()["error"] == {"code": "VALIDATION_ERROR", "message": "request validation failed", "request_id": request_id}
    test_app = FastAPI()
    install_http_contract(test_app)

    @test_app.get("/boom")
    def boom():
        raise RuntimeError("private detail must not be returned")

    failure = TestClient(test_app, raise_server_exceptions=False).get("/boom", headers={"X-Request-ID": request_id})
    assert failure.status_code == 500
    assert failure.json()["error"] == {"code": "INTERNAL_ERROR", "message": "internal service error", "request_id": request_id}
    print(json.dumps({"service": args.service, "health": "PASS", "request_id": "PASS", "validation_error": "PASS", "internal_error": "PASS"}))


if __name__ == "__main__":
    main()
