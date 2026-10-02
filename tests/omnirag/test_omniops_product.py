from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from apps.omniops.api.config import Settings
from apps.omniops.api.demo_data import seed_demo
from apps.omniops.api.services import OmniOpsService
from apps.omniops.api.store import Store


class OmniOpsProductTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.settings = Settings(
            host="127.0.0.1", port=8090, mode="demo", data_root=root,
            database_path=root / "db.sqlite", upload_root=root / "uploads",
            ragflow_api_root="http://127.0.0.1:9380/api/v1", ragflow_api_key="", ragflow_chat_id="",
            max_upload_mb=1, enable_demo_seed=True,
        )
        self.store = Store(self.settings.database_path)
        seed_demo(self.store)
        self.service = OmniOpsService(self.settings, self.store)

    def tearDown(self):
        self.tmp.cleanup()

    def test_seed_contains_multimodal_incident(self):
        incident = self.store.get_incident("INC-20260922-001")
        self.assertIsNotNone(incident)
        kinds = {x["kind"] for x in incident["evidence"]}
        self.assertIn("image", kinds)
        self.assertIn("log", kinds)

    def test_demo_analysis_persists_trace(self):
        result = self.service.analyze_incident("INC-20260922-001")
        self.assertIn(result.decision, {"pass", "abstain"})
        self.assertGreater(len(result.answer), 20)
        steps = self.store.query("SELECT * FROM trace_steps WHERE run_id=? ORDER BY step_no", (result.run_id,))
        self.assertGreaterEqual(len(steps), 5)
        self.assertTrue(any(x["component"] == "omnirag/verifier" for x in steps))

    def test_tool_audit_is_read_only_demo(self):
        result = self.service.analyze_incident("INC-20260922-001")
        audit = self.store.one("SELECT * FROM tool_audit WHERE run_id=?", (result.run_id,))
        self.assertEqual(audit["risk"], "read")
        self.assertEqual(audit["policy"], "allow")

    def test_upload_rejects_unsupported_extension(self):
        with self.assertRaises(ValueError):
            self.service.upload_asset("payload.exe", "exe", b"x")

    def test_upload_stages_supported_asset(self):
        row = self.service.upload_asset("note.txt", "txt", b"hello")
        self.assertEqual(row["status"], "local_staged")
        self.assertTrue(Path(row["local_path"]).exists())

    def test_metrics_do_not_claim_live_results(self):
        rows = self.store.query("SELECT * FROM evaluation_metrics")
        metric = {x["key"]: x for x in rows}
        self.assertEqual(metric["retrieval_recall5"]["status"], "not_run")
        self.assertEqual(metric["agent_task_success"]["status"], "not_run")


if __name__ == "__main__":
    unittest.main()
