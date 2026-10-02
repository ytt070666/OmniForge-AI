from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")


async def retry_async(
    fn: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    base_delay: float = 0.05,
    retry_on: tuple[type[BaseException], ...] = (TimeoutError, OSError),
) -> T:
    """Small bounded retry helper; never retries indefinitely."""
    if attempts < 1:
        raise ValueError("attempts must be >= 1")
    last: BaseException | None = None
    for index in range(attempts):
        try:
            return await fn()
        except retry_on as exc:
            last = exc
            if index + 1 >= attempts:
                raise
            await asyncio.sleep(base_delay * (2**index))
    assert last is not None
    raise last


@dataclass
class _BreakerState:
    failures: int = 0
    opened_at: float | None = None


class AsyncCircuitBreaker:
    """Process-local circuit breaker used by the learning gateway.

    Production deployments can replace this with a Redis-backed/shared breaker,
    but the state transitions remain the same and are unit-testable here.
    """

    def __init__(self, *, failure_threshold: int = 3, reset_after: float = 10.0):
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        self.failure_threshold = failure_threshold
        self.reset_after = reset_after
        self.state = _BreakerState()
        self._lock = asyncio.Lock()

    async def call(self, fn: Callable[[], Awaitable[T]]) -> T:
        async with self._lock:
            if self.state.opened_at is not None:
                elapsed = time.monotonic() - self.state.opened_at
                if elapsed < self.reset_after:
                    raise RuntimeError("circuit_open")
                self.state = _BreakerState()
        try:
            result = await fn()
        except Exception:
            async with self._lock:
                self.state.failures += 1
                if self.state.failures >= self.failure_threshold:
                    self.state.opened_at = time.monotonic()
            raise
        async with self._lock:
            self.state = _BreakerState()
        return result


class AsyncConcurrencyGate:
    """Backpressure primitive for expensive model/RAG paths."""

    def __init__(self, limit: int):
        if limit < 1:
            raise ValueError("limit must be >= 1")
        self.limit = limit
        self._semaphore = asyncio.Semaphore(limit)

    async def run(self, fn: Callable[[], Awaitable[T]]) -> T:
        async with self._semaphore:
            return await fn()
