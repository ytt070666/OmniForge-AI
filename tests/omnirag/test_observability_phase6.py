from pathlib import Path

import pytest

from extensions.omnirag.observability.events import TraceEvent, hash_identifier
from extensions.omnirag.observability.metrics import aggregate


def test_trace_event_contains_no_raw_prompt_or_completion_fields():
    event = TraceEvent(trace_id="t", component="llm", operation="generate", status="ok", latency_ms=12.5, input_tokens=10, output_tokens=4)
    payload = event.as_dict()
    assert "prompt" not in payload
    assert "completion" not in payload
    assert "tool_arguments" not in payload


def test_trace_tags_reject_high_cardinality_blob():
    with pytest.raises(ValueError):
        TraceEvent(trace_id="t", component="x", operation="y", status="ok", latency_ms=1, tags={"query": "x" * 120})


def test_identifier_hash_is_stable_but_not_plaintext():
    digest = hash_identifier("session-123")
    assert digest == hash_identifier("session-123")
    assert "session-123" not in digest


def test_aggregate_does_not_invent_cost_without_price_table():
    report = aggregate(
        [
            {"component": "llm", "status": "ok", "latency_ms": 100, "model": "m", "input_tokens": 1000, "output_tokens": 100, "tool_calls": 0, "tool_failures": 0},
            {"component": "tool", "status": "error", "latency_ms": 20, "tool_calls": 1, "tool_failures": 1, "abstained": True},
        ]
    )
    assert report["cost"] is None
    assert report["tools"]["success_rate"] == 0.0
    assert report["abstain_count"] == 1


def test_aggregate_cost_only_uses_explicit_prices():
    report = aggregate(
        [{"component": "llm", "status": "ok", "latency_ms": 1, "model": "m", "input_tokens": 1_000_000, "output_tokens": 500_000}],
        price_table={"m": {"input_per_million_usd": 1.0, "output_per_million_usd": 2.0}},
    )
    assert report["cost"]["estimated_usd"] == 2.0
