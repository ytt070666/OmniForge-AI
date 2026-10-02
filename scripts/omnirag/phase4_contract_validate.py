#!/usr/bin/env python3
"""Validate deterministic Phase-4 agent-governance contracts offline."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from extensions.omnirag.agent.controller import MemoryAwareAgentController
from extensions.omnirag.agent.critic import EvidenceCriticV1
from extensions.omnirag.agent.memory_policy import select_planning_memories
from extensions.omnirag.agent.ragflow_governance import merge_critic_into_rag_verdict

SCENARIOS = ROOT / "benchmarks" / "omnirag" / "phase4" / "scenarios.jsonl"


def _load() -> list[dict]:
    rows = [json.loads(line) for line in SCENARIOS.read_text(encoding="utf-8").splitlines() if line.strip()]
    ids = [row.get("id") for row in rows]
    assert all(ids), "every scenario needs an id"
    assert len(ids) == len(set(ids)), "scenario ids must be unique"
    return rows


def _critic(row: dict) -> None:
    out = EvidenceCriticV1().decide(
        original_query=row["query"],
        answer=row.get("answer", ""),
        verification=row.get("verification") or {},
        rag_verdict=row.get("rag_verdict") or {},
        retries_used=int(row.get("retries_used", 0)),
        retry_budget=int(row.get("retry_budget", 0)),
    )
    assert out.action.value == row["expect_action"], (row["id"], out.as_dict())
    if out.action.value == "retrieve_more":
        assert out.retry_query.strip(), f"{row['id']}: retry must have a focus query"


def _memory(row: dict) -> None:
    items = select_planning_memories(row["query"], row.get("rows") or [])
    assert [x.message_id for x in items] == row["expect_message_ids"], row["id"]
    if "expect_rank" in row:
        assert items and items[0].source_rank == row["expect_rank"], row["id"]
        assert 0 < items[0].rank_score <= 1, row["id"]


def _merge(row: dict) -> None:
    out = merge_critic_into_rag_verdict(row.get("rag_verdict") or {}, row.get("governance") or {})
    assert out.get("status") == row["expect_status"], (row["id"], out)


async def _controller(row: dict) -> None:
    attempts = list(row.get("attempts") or [])
    idx = 0
    persisted: list[str] = []

    async def research(query: str, **kwargs):
        nonlocal idx
        chosen = attempts[min(idx, len(attempts) - 1)] if attempts else {}
        idx += 1
        return {**chosen, "chunks": [{"chunk_id": f"c{idx}"}]}

    async def persist(text: str):
        persisted.append(text)

    out = await MemoryAwareAgentController().run(row["query"], research=research, persist=persist)
    assert out.action.value == row["expect_action"], (row["id"], out.as_dict())
    if "expect_attempts" in row:
        assert len(out.trace.attempts) == row["expect_attempts"], row["id"]
    assert bool(persisted) is bool(row.get("expect_persist", False)), row["id"]
    for text in persisted:
        assert "Latency is 42 ms" not in text, f"{row['id']}: answer fact leaked into strategy memory"


async def main() -> int:
    rows = _load()
    counts: dict[str, int] = {}
    for row in rows:
        kind = row.get("type")
        counts[kind] = counts.get(kind, 0) + 1
        if kind == "critic":
            _critic(row)
        elif kind == "memory":
            _memory(row)
        elif kind == "merge":
            _merge(row)
        elif kind == "controller":
            await _controller(row)
        else:
            raise AssertionError(f"unknown scenario type: {kind!r}")
    print(f"Phase-4 contract scenarios: PASS ({len(rows)} total; {counts})")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
