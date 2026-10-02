from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


class RagflowError(RuntimeError):
    pass


@dataclass(frozen=True)
class RagflowAnswer:
    answer: str
    reference: dict[str, Any] | list[Any] | None
    latency_ms: float


class RagflowClient:
    def __init__(self, api_root: str, api_key: str, chat_id: str, timeout: int = 180):
        self.api_root = api_root.rstrip("/")
        self.api_key = api_key
        self.chat_id = chat_id
        self.timeout = timeout

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.api_root}/{path.lstrip('/')}"
        payload = None if body is None else json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=payload, method=method)
        req.add_header("Authorization", f"Bearer {self.api_key}")
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1000]
            raise RagflowError(f"RAGFlow HTTP {exc.code}: {detail}") from exc
        except OSError as exc:
            raise RagflowError(f"RAGFlow connection failed: {exc}") from exc
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RagflowError("RAGFlow returned non-JSON response") from exc
        if not isinstance(obj, dict) or obj.get("code") not in (None, 0):
            raise RagflowError(f"RAGFlow API error: {obj}")
        return obj

    def ping(self) -> dict[str, Any]:
        return self._request("GET", "system/ping")

    def chat(self, question: str) -> RagflowAnswer:
        started = time.perf_counter()
        obj = self._request("POST", "chat/completions", {
            "chat_id": self.chat_id,
            "messages": [{"role": "user", "content": question}],
            "stream": False,
            "pass_all_history_messages": True,
            "store_history_messages": False,
        })
        elapsed = (time.perf_counter() - started) * 1000
        data = obj.get("data") or {}
        return RagflowAnswer(answer=str(data.get("answer") or ""), reference=data.get("reference"), latency_ms=round(elapsed, 2))
