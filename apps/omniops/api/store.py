from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS incidents (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  severity TEXT NOT NULL,
  status TEXT NOT NULL,
  asset_id TEXT NOT NULL DEFAULT '',
  summary TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS evidence (
  id TEXT PRIMARY KEY,
  incident_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  title TEXT NOT NULL,
  source TEXT NOT NULL,
  content TEXT NOT NULL DEFAULT '',
  asset_url TEXT NOT NULL DEFAULT '',
  confidence REAL NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  FOREIGN KEY(incident_id) REFERENCES incidents(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS agent_runs (
  id TEXT PRIMARY KEY,
  incident_id TEXT,
  query TEXT NOT NULL,
  status TEXT NOT NULL,
  decision TEXT NOT NULL,
  answer TEXT NOT NULL,
  confidence REAL NOT NULL DEFAULT 0,
  retry_count INTEGER NOT NULL DEFAULT 0,
  latency_ms REAL NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS trace_steps (
  id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  step_no INTEGER NOT NULL,
  name TEXT NOT NULL,
  component TEXT NOT NULL,
  status TEXT NOT NULL,
  detail TEXT NOT NULL DEFAULT '',
  latency_ms REAL NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  FOREIGN KEY(run_id) REFERENCES agent_runs(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS tool_audit (
  id TEXT PRIMARY KEY,
  run_id TEXT,
  tool_name TEXT NOT NULL,
  risk TEXT NOT NULL,
  policy TEXT NOT NULL,
  status TEXT NOT NULL,
  latency_ms REAL NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS knowledge_assets (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  kind TEXT NOT NULL,
  status TEXT NOT NULL,
  source TEXT NOT NULL,
  size_bytes INTEGER NOT NULL DEFAULT 0,
  local_path TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS evaluation_metrics (
  key TEXT PRIMARY KEY,
  label TEXT NOT NULL,
  value TEXT NOT NULL,
  status TEXT NOT NULL,
  category TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS chat_messages (
  id TEXT PRIMARY KEY,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  citations_json TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL
);
"""


class Store:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init()

    @contextmanager
    def conn(self) -> Iterator[sqlite3.Connection]:
        con = sqlite3.connect(self.path, timeout=15, check_same_thread=False)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        try:
            yield con
            con.commit()
        finally:
            con.close()

    def _init(self) -> None:
        with self.conn() as con:
            con.executescript(SCHEMA)

    def clear_demo(self) -> None:
        with self._lock, self.conn() as con:
            for table in ("trace_steps", "tool_audit", "agent_runs", "evidence", "incidents", "knowledge_assets", "evaluation_metrics", "chat_messages"):
                con.execute(f"DELETE FROM {table}")

    def insert(self, table: str, row: dict[str, Any]) -> None:
        with self._lock, self.conn() as con:
            cols = list(row)
            placeholders = ",".join("?" for _ in cols)
            con.execute(f"INSERT OR REPLACE INTO {table} ({','.join(cols)}) VALUES ({placeholders})", [row[c] for c in cols])

    def query(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self._lock, self.conn() as con:
            return [dict(r) for r in con.execute(sql, params).fetchall()]

    def one(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def list_incidents(self) -> list[dict[str, Any]]:
        return self.query("SELECT * FROM incidents ORDER BY created_at DESC")

    def get_incident(self, incident_id: str) -> dict[str, Any] | None:
        incident = self.one("SELECT * FROM incidents WHERE id=?", (incident_id,))
        if not incident:
            return None
        incident["evidence"] = self.query("SELECT * FROM evidence WHERE incident_id=? ORDER BY created_at", (incident_id,))
        incident["runs"] = self.query("SELECT * FROM agent_runs WHERE incident_id=? ORDER BY created_at DESC", (incident_id,))
        return incident

    def create_incident(self, title: str, severity: str, asset_id: str, summary: str = "") -> dict[str, Any]:
        now = utcnow()
        incident_id = f"INC-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        row = {"id": incident_id, "title": title, "severity": severity, "status": "open", "asset_id": asset_id, "summary": summary, "created_at": now, "updated_at": now}
        self.insert("incidents", row)
        return row

    def add_run(self, row: dict[str, Any], steps: list[dict[str, Any]]) -> None:
        self.insert("agent_runs", row)
        for step in steps:
            self.insert("trace_steps", step)

    def add_chat(self, role: str, content: str, citations: list[dict[str, Any]] | None = None) -> None:
        self.insert("chat_messages", {"id": uuid.uuid4().hex, "role": role, "content": content, "citations_json": json.dumps(citations or [], ensure_ascii=False), "created_at": utcnow()})

    def chat_history(self, limit: int = 40) -> list[dict[str, Any]]:
        rows = self.query("SELECT * FROM chat_messages ORDER BY created_at DESC LIMIT ?", (limit,))
        rows.reverse()
        for row in rows:
            row["citations"] = json.loads(row.pop("citations_json", "[]"))
        return rows
