"""Execution guard layered on top of RAGFlow's existing ToolCallSession."""

from __future__ import annotations

import hashlib
import hmac
import inspect
import json
import secrets
import time
from collections import Counter
from collections.abc import Callable, Mapping
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

from .policy import ToolPolicy
from .registry import ToolRegistry
from .types import ToolCallEvent

TraceSink = Callable[[list[dict[str, Any]]], Any]


def _argument_fingerprint(arguments: Mapping[str, Any], key: bytes) -> str:
    encoded = json.dumps(arguments, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":")).encode("utf-8")
    return hmac.new(key, encoded, hashlib.sha256).hexdigest()


def _validate_arguments(schema: dict[str, Any], arguments: Mapping[str, Any]) -> None:
    # MCP/OpenAI schemas are JSON Schema objects. Draft 2020-12 accepts the
    # common object/required/properties subset used by RAGFlow tools. Avoid
    # leaking argument values through jsonschema's verbose exception text.
    try:
        Draft202012Validator.check_schema(schema or {"type": "object"})
        Draft202012Validator(schema or {"type": "object"}).validate(dict(arguments))
    except SchemaError as exc:
        raise ValueError("Tool definition contains an invalid JSON Schema") from exc
    except ValidationError as exc:
        raise ValueError("Tool arguments failed JSON Schema validation") from exc


class GovernedToolCallSession:
    """Allowlist, schema validation, budget and audit without reimplementing tools."""

    def __init__(
        self,
        base_session: object,
        registry: ToolRegistry,
        allowed_names: tuple[str, ...],
        policy: ToolPolicy,
        trace_sink: TraceSink | None = None,
    ) -> None:
        self.base_session = base_session
        self.registry = registry
        self.allowed_names = frozenset(allowed_names)
        self.policy = policy
        self.trace_sink = trace_sink
        self.total_calls = 0
        self.calls_by_tool: Counter[str] = Counter()
        self._events: list[ToolCallEvent] = []
        self._audit_hmac_key = secrets.token_bytes(32)

    def _check(self, name: str, arguments: Mapping[str, Any]) -> None:
        descriptor = self.registry.get(name)
        if descriptor is None:
            raise PermissionError(f"Tool '{name}' is not registered")
        if name not in self.allowed_names:
            raise PermissionError(f"Tool '{name}' is outside the per-query shortlist")
        ok, reason = self.policy.permits(descriptor)
        if not ok:
            raise PermissionError(f"Tool '{name}' denied by policy: {reason}")
        if self.total_calls >= self.policy.max_total_calls:
            raise RuntimeError(f"Tool-call budget exhausted ({self.policy.max_total_calls} total calls)")
        if self.calls_by_tool[name] >= self.policy.max_calls_per_tool:
            raise RuntimeError(f"Per-tool budget exhausted for '{name}' ({self.policy.max_calls_per_tool} calls)")
        if not isinstance(arguments, Mapping):
            raise TypeError(f"Tool arguments for {name} must be an object")
        _validate_arguments(descriptor.parameters, arguments)

    def _record(self, name: str, arguments: Mapping[str, Any], *, ok: bool, elapsed: float, error_type: str = "") -> None:
        descriptor = self.registry.get(name)
        event = ToolCallEvent(
            tool_name=name,
            source=descriptor.source.value if descriptor else "unknown",
            risk=descriptor.risk.value if descriptor else "unknown",
            ok=ok,
            elapsed_seconds=round(max(0.0, elapsed), 6),
            argument_keys=tuple(sorted(str(k) for k in arguments.keys())),
            arguments_hmac_sha256=_argument_fingerprint(arguments, self._audit_hmac_key),
            error_type=error_type[:100],
        )
        self._events.append(event)
        if self.trace_sink is not None:
            result = self.trace_sink(self.trace_snapshot())
            # Current RAGFlow integration supplies a synchronous sink. Do not
            # schedule an unowned coroutine if a future caller passes async.
            if inspect.isawaitable(result):
                close = getattr(result, "close", None)
                if callable(close):
                    close()

    def trace_snapshot(self) -> list[dict[str, Any]]:
        return [
            {
                "tool_name": e.tool_name,
                "source": e.source,
                "risk": e.risk,
                "ok": e.ok,
                "elapsed_seconds": e.elapsed_seconds,
                "argument_keys": list(e.argument_keys),
                "arguments_hmac_sha256": e.arguments_hmac_sha256,
                "error_type": e.error_type,
            }
            for e in self._events
        ]

    async def tool_call_async(self, name: str, arguments: dict[str, Any], request_timeout: float | int | None = None) -> Any:
        args = arguments if isinstance(arguments, Mapping) else {}
        started = time.perf_counter()
        try:
            self._check(name, args)
            self.total_calls += 1
            self.calls_by_tool[name] += 1
            if hasattr(self.base_session, "tool_call_async"):
                result = await self.base_session.tool_call_async(name, dict(args), request_timeout=request_timeout)
            else:
                import asyncio

                result = await asyncio.to_thread(self.base_session.tool_call, name, dict(args), request_timeout or 10)
            self._record(name, args, ok=True, elapsed=time.perf_counter() - started)
            return result
        except Exception as exc:
            self._record(name, args, ok=False, elapsed=time.perf_counter() - started, error_type=type(exc).__name__)
            raise

    def tool_call(self, name: str, arguments: dict[str, Any], timeout: float | int | None = None) -> Any:
        import asyncio

        return asyncio.run(self.tool_call_async(name, arguments, request_timeout=timeout))
