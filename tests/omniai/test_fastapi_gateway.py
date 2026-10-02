from __future__ import annotations

import importlib
import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient


class GatewayHTTPTests(unittest.TestCase):
    def test_health_and_modules(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"OMNIOPS_DATA_ROOT": temp, "OMNIOPS_MODE": "demo"}, clear=False):
            module = importlib.import_module("services.omniai_gateway.app")
            client = TestClient(module.app)
            health = client.get("/api/v1/health")
            self.assertEqual(health.status_code, 200)
            self.assertTrue(health.json()["ok"])
            modules = client.get("/api/v1/platform/modules")
            self.assertEqual(modules.status_code, 200)
            self.assertTrue(any(row["id"] == "langgraph" for row in modules.json()["items"]))


if __name__ == "__main__":
    unittest.main()
