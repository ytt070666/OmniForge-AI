"""Check the saved synthetic Keras model through the severity API."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient
from services.omniai_tensorflow.app import app


def main() -> None:
    client = TestClient(app)
    health = client.get("/health").json()
    result = client.post("/api/v1/severity", json={"text": "dns beacon attack detected on gateway"}).json()
    assert health["installed"] and health["model_ready"]
    assert result["severity"] in {"low", "medium", "high", "critical"}
    assert 0 <= result["probability"] <= 1 and result["synthetic_model"] is True
    print(json.dumps({"tensorflow": health["framework_version"], "severity": result["severity"], "probability": result["probability"]}))


if __name__ == "__main__":
    main()
