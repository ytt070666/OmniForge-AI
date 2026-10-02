from __future__ import annotations

import asyncio
import importlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from labs.vector_lab.cosine_search import VectorRecord, cosine, top_k
from omniai_platform.idempotency import InMemoryIdempotencyStore
from omniai_platform.jobs import LocalJobManager
from omniai_platform.modules import default_modules
from services.omniai_agent.graph import final_decision, route_after_verify


class ModularPlatformTests(unittest.TestCase):
    def test_vector_lab_cosine_and_topk(self):
        self.assertAlmostEqual(cosine([1, 0], [1, 0]), 1.0)
        rows = [VectorRecord("b", (0.0, 1.0)), VectorRecord("a", (1.0, 0.0))]
        result = top_k((0.9, 0.1), rows, 1)
        self.assertEqual(result[0][1].id, "a")

    def test_langgraph_retry_contract_is_bounded(self):
        state = {"verification": {"decision": "retrieve_more"}, "retry_count": 0, "max_retries": 1}
        self.assertEqual(route_after_verify(state), "retry")
        state["retry_count"] = 1
        self.assertEqual(route_after_verify(state), "finish")
        self.assertEqual(final_decision(state), "abstain")

    def test_module_registry_covers_learning_stack(self):
        ids = {row.id for row in default_modules()}
        for expected in {"ragflow", "omnirag", "fastapi", "langgraph", "langchain", "llamaindex", "milvus", "nats", "tensorflow", "go_realtime", "nestjs_bff", "spring_connector"}:
            self.assertIn(expected, ids)

    def test_idempotency_store(self):
        async def run():
            store = InMemoryIdempotencyStore(ttl_seconds=30)
            self.assertIsNone(await store.get("k"))
            await store.put("k", {"run": 1})
            self.assertEqual(await store.get("k"), {"run": 1})
        asyncio.run(run())

    def test_local_job_manager_contract(self):
        async def run():
            jobs = LocalJobManager()
            job = await jobs.submit("INC-1", lambda _run: asyncio.sleep(0.01, result={"ok": True}))
            for _ in range(50):
                value = await jobs.get(job.run_id)
                if value and value.state == "completed":
                    break
                await asyncio.sleep(0.01)
            self.assertIsNotNone(value)
            self.assertEqual(value.state, "completed")
            self.assertEqual(value.result, {"ok": True})
        asyncio.run(run())

    def test_upstream_inventory_is_permissive_only(self):
        data = json.loads(Path("config/omniai/upstreams.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["components"]), 10)
        licenses = {item["license"] for item in data["components"]}
        self.assertTrue(licenses <= {"MIT", "Apache-2.0"})

    def test_gateway_openapi_has_versioned_async_contract(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"OMNIOPS_DATA_ROOT": temp, "OMNIOPS_MODE": "demo"}, clear=False):
            module = importlib.import_module("services.omniai_gateway.app")
            schema = module.app.openapi()
        paths = schema["paths"]
        self.assertIn("/api/v1/analyses", paths)
        self.assertIn("/api/v1/analyses/{run_id}", paths)
        self.assertIn("/api/v1/platform/modules", paths)
        self.assertIn("/api/v1/chat", paths)

    def test_omniops_ui_uses_versioned_api(self):
        text = Path("apps/omniops/web/app.js").read_text(encoding="utf-8")
        self.assertIn("/api/v1/analyses", text)
        self.assertNotIn("'/api/overview'", text)


if __name__ == "__main__":
    unittest.main()
