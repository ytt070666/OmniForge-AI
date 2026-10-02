"""Aggregate latency/token/tool metrics without inventing prices or quality."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Iterable


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs) - 1) * p
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return xs[lo]
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def aggregate(events: Iterable[dict], price_table: dict[str, dict[str, float]] | None = None) -> dict:
    rows = list(events)
    latencies = [float(x["latency_ms"]) for x in rows if x.get("latency_ms") is not None]
    statuses = Counter(x.get("status", "unknown") for x in rows)
    input_tokens = sum(int(x.get("input_tokens") or 0) for x in rows)
    output_tokens = sum(int(x.get("output_tokens") or 0) for x in rows)
    tool_calls = sum(int(x.get("tool_calls") or 0) for x in rows)
    tool_failures = sum(int(x.get("tool_failures") or 0) for x in rows)
    retries = sum(int(x.get("retry_count") or 0) for x in rows)
    abstains = sum(bool(x.get("abstained")) for x in rows)
    components = defaultdict(list)
    for row in rows:
        if row.get("latency_ms") is not None:
            components[row.get("component", "unknown")].append(float(row["latency_ms"]))

    cost = None
    if price_table:
        total = 0.0
        priced = 0
        for row in rows:
            model = row.get("model")
            prices = price_table.get(model) if model else None
            if not prices:
                continue
            total += (int(row.get("input_tokens") or 0) / 1_000_000) * float(prices.get("input_per_million_usd", 0.0))
            total += (int(row.get("output_tokens") or 0) / 1_000_000) * float(prices.get("output_per_million_usd", 0.0))
            priced += 1
        cost = {"estimated_usd": round(total, 8), "priced_events": priced, "unpriced_events": len(rows) - priced}

    return {
        "events": len(rows),
        "status_counts": dict(sorted(statuses.items())),
        "latency_ms": {
            "mean": sum(latencies) / len(latencies) if latencies else None,
            "p50": percentile(latencies, 0.50),
            "p95": percentile(latencies, 0.95),
            "max": max(latencies) if latencies else None,
        },
        "component_latency_ms": {
            key: {"p50": percentile(vals, 0.50), "p95": percentile(vals, 0.95), "count": len(vals)}
            for key, vals in sorted(components.items())
        },
        "tokens": {"input": input_tokens, "output": output_tokens, "total": input_tokens + output_tokens},
        "tools": {
            "calls": tool_calls,
            "failures": tool_failures,
            "success_rate": (tool_calls - tool_failures) / tool_calls if tool_calls else None,
        },
        "retry_count": retries,
        "abstain_count": abstains,
        "cost": cost,
    }
