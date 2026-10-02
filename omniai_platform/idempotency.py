from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class _Entry:
    value: Any
    expires_at: float


class InMemoryIdempotencyStore:
    def __init__(self, ttl_seconds: float = 900.0):
        self.ttl_seconds = ttl_seconds
        self._items: dict[str, _Entry] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        async with self._lock:
            entry = self._items.get(key)
            if not entry:
                return None
            if entry.expires_at <= time.monotonic():
                self._items.pop(key, None)
                return None
            return entry.value

    async def put(self, key: str, value: Any) -> None:
        async with self._lock:
            self._items[key] = _Entry(value=value, expires_at=time.monotonic() + self.ttl_seconds)
