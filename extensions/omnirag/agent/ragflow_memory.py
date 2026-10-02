"""Lazy RAGFlow memory-store adapter for Phase-4 planning context.

The adapter keeps long-term memory outside the factual evidence path. Recall is
restricted to explicitly configured memories owned by the current tenant and is
filtered to procedural/episodic messages before it reaches the router prompt.
Writes are opt-in, tenant-checked, and contain strategy/process metadata only.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from .memory_policy import render_planning_memory_context, select_planning_memories


def _flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _normalize_ids(memory_ids: list[str] | tuple[str, ...] | None) -> list[str]:
    return list(dict.fromkeys(str(mid).strip() for mid in (memory_ids or []) if str(mid).strip()))


async def recall_planning_memory(
    query: str,
    memory_ids: list[str] | tuple[str, ...] | None,
    *,
    tenant_id: str = "",
    user_id: str = "",
    agent_id: str = "",
    session_id: str = "",
    allowed_types: tuple[str, ...] = ("procedural", "episodic"),
    top_n: int = 5,
) -> tuple[list, str]:
    """Recall strategy memories without exposing them as evidence.

    Memory IDs are explicitly allow-listed and tenant ownership is checked here
    instead of trusting request parameters. The public RAGFlow memory-search
    result does not expose raw similarity scores, so downstream ranking uses the
    source order plus transparent lexical/recency tie-breakers.
    """

    requested_ids = _normalize_ids(memory_ids)
    if not _flag("OMNIRAG_AGENT_MEMORY", False) or not requested_ids:
        return [], ""

    from api.db.services.memory_service import MemoryService
    from api.db.joint_services.memory_message_service import query_message

    memories = list(MemoryService.get_by_ids(requested_ids) or [])
    safe_ids = [m.id for m in memories if (not tenant_id or str(getattr(m, "tenant_id", "")) == str(tenant_id))]
    if not safe_ids:
        return [], ""

    filter_dict: dict[str, Any] = {"memory_id": safe_ids}
    if user_id:
        filter_dict["user_id"] = user_id
    if agent_id:
        filter_dict["agent_id"] = agent_id
    if session_id:
        filter_dict["session_id"] = session_id
    params = {
        "query": query,
        "similarity_threshold": float(os.getenv("OMNIRAG_AGENT_MEMORY_SIMILARITY_THRESHOLD", "0.15")),
        "keywords_similarity_weight": float(os.getenv("OMNIRAG_AGENT_MEMORY_KEYWORD_WEIGHT", "0.7")),
        "top_n": max(8, int(top_n) * 3),
    }
    rows = await asyncio.to_thread(query_message, filter_dict, params)
    items = select_planning_memories(query, rows, allowed_types=allowed_types, top_n=top_n)
    return items, render_planning_memory_context(items)


async def persist_strategy_memory(
    memory_ids: list[str] | tuple[str, ...] | None,
    *,
    tenant_id: str,
    user_id: str,
    agent_id: str,
    session_id: str,
    strategy_record: str,
) -> tuple[bool, str]:
    """Queue a strategy-only experience record after a successful run.

    Auto-write is opt-in. By default, a memory configuration that includes
    semantic extraction is rejected because generated agent experience must not
    silently become a parallel factual knowledge base. Raw-only memories are
    also skipped: a strategy record is useful only when procedural/episodic
    extraction is configured.
    """

    requested_ids = _normalize_ids(memory_ids)
    if not _flag("OMNIRAG_AGENT_MEMORY_WRITE", False) or not requested_ids:
        return True, "memory write disabled"
    if not (strategy_record or "").strip():
        return False, "empty strategy record"

    from common.constants import MemoryType
    from api.db.services.memory_service import MemoryService
    from api.db.joint_services.memory_message_service import queue_save_to_memory_task

    allow_semantic = _flag("OMNIRAG_AGENT_ALLOW_SEMANTIC_MEMORY_WRITE", False)
    strategy_bits = MemoryType.PROCEDURAL.value | MemoryType.EPISODIC.value
    safe_ids: list[str] = []
    for memory in MemoryService.get_by_ids(requested_ids) or []:
        if tenant_id and str(getattr(memory, "tenant_id", "")) != str(tenant_id):
            continue
        memory_type = int(getattr(memory, "memory_type", 0) or 0)
        if not (memory_type & strategy_bits):
            continue
        if not allow_semantic and (memory_type & MemoryType.SEMANTIC.value):
            continue
        safe_ids.append(memory.id)
    if not safe_ids:
        return False, "no eligible tenant-owned procedural/episodic memory"

    # RAGFlow always stores a RAW envelope before optional extraction. Keep even
    # that envelope fact-free: neither the user's question nor the generated
    # answer is written into long-term strategy memory.
    message = {
        "user_id": user_id,
        "agent_id": agent_id,
        "session_id": session_id,
        "user_input": "OmniRAG strategy-memory event after an accepted evidence-governed run.",
        "agent_response": strategy_record,
    }
    return await queue_save_to_memory_task(safe_ids, message)
