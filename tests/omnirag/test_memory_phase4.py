from datetime import datetime, timezone

from extensions.omnirag.agent.memory_policy import (
    normalize_ragflow_memory_results,
    render_planning_memory_context,
    select_planning_memories,
)


def test_planning_memory_filters_raw_and_semantic_by_default():
    rows = [
        {"memory_id": "m", "message_id": "1", "message_type": "raw", "content": "raw conversation", "valid_at": "2026-09-16 10:00:00"},
        {"memory_id": "m", "message_id": "2", "message_type": "semantic", "content": "The system uses port 9380", "valid_at": "2026-09-16 10:00:00"},
        {"memory_id": "m", "message_id": "3", "message_type": "procedural", "content": "When evidence conflicts, rerun retrieval with the unresolved claim.", "valid_at": "2026-09-16 10:00:00"},
    ]
    items = normalize_ragflow_memory_results("resolve evidence conflict", rows, now=datetime(2026, 9, 17, tzinfo=timezone.utc))
    assert [x.message_id for x in items] == ["3"]


def test_rank_is_explicit_relevance_signal_not_fabricated_similarity():
    rows = [
        {"memory_id": "m", "message_id": "1", "message_type": "procedural", "content": "Use targeted retrieval after a failed evidence gate.", "valid_at": "2026-09-16 10:00:00"},
        {"memory_id": "m", "message_id": "2", "message_type": "procedural", "content": "Use targeted retrieval after a failed evidence gate.", "valid_at": "2026-09-16 10:00:00"},
    ]
    items = normalize_ragflow_memory_results("targeted retrieval", rows, now=datetime(2026, 9, 17, tzinfo=timezone.utc))
    # Duplicate content is removed and the public contract exposes rank-derived
    # relevance rather than pretending RAGFlow returned a raw similarity score.
    assert len(items) == 1
    assert items[0].source_rank == 1
    assert 0 < items[0].rank_score <= 1


def test_memory_context_is_labeled_non_evidence():
    rows = [
        {"memory_id": "m", "message_id": "1", "message_type": "episodic", "content": "A previous chart query needed visual retrieval.", "valid_at": "2026-09-16 10:00:00"}
    ]
    items = select_planning_memories("chart query", rows, now=datetime(2026, 9, 17, tzinfo=timezone.utc))
    text = render_planning_memory_context(items)
    assert "strategy context only" in text
    assert "Do NOT treat them as factual evidence" in text


def test_memory_recall_enforces_tenant_boundary(monkeypatch):
    import asyncio
    import sys
    import types

    from extensions.omnirag.agent.ragflow_memory import recall_planning_memory

    class Mem:
        def __init__(self, mid, tenant):
            self.id = mid
            self.tenant_id = tenant

    class FakeMemoryService:
        @staticmethod
        def get_by_ids(ids):
            return [Mem("mine", "tenant-a"), Mem("other", "tenant-b")]

    captured = {}

    def fake_query_message(filter_dict, params):
        captured["ids"] = list(filter_dict["memory_id"])
        return [
            {
                "memory_id": "mine",
                "message_id": "1",
                "message_type": "procedural",
                "content": "Use targeted retrieval after a failed evidence gate.",
                "valid_at": "2026-09-16 10:00:00",
            }
        ]

    memory_mod = types.ModuleType("api.db.services.memory_service")
    memory_mod.MemoryService = FakeMemoryService
    joint_mod = types.ModuleType("api.db.joint_services.memory_message_service")
    joint_mod.query_message = fake_query_message
    monkeypatch.setitem(sys.modules, "api.db.services.memory_service", memory_mod)
    monkeypatch.setitem(sys.modules, "api.db.joint_services.memory_message_service", joint_mod)
    monkeypatch.setenv("OMNIRAG_AGENT_MEMORY", "1")

    items, context = asyncio.run(recall_planning_memory("targeted retrieval", ["mine", "other"], tenant_id="tenant-a"))
    assert captured["ids"] == ["mine"]
    assert len(items) == 1
    assert "strategy context only" in context


def test_strategy_memory_write_is_tenant_scoped_and_fact_free(monkeypatch):
    import asyncio
    import sys
    import types

    from common.constants import MemoryType
    from extensions.omnirag.agent.ragflow_memory import persist_strategy_memory

    class Mem:
        def __init__(self, mid, tenant, memory_type):
            self.id = mid
            self.tenant_id = tenant
            self.memory_type = memory_type

    class FakeMemoryService:
        @staticmethod
        def get_by_ids(ids):
            return [
                Mem("mine", "tenant-a", MemoryType.PROCEDURAL.value),
                Mem("other", "tenant-b", MemoryType.PROCEDURAL.value),
                Mem("semantic", "tenant-a", MemoryType.PROCEDURAL.value | MemoryType.SEMANTIC.value),
            ]

    captured = {}

    async def fake_queue(memory_ids, message):
        captured["ids"] = list(memory_ids)
        captured["message"] = dict(message)
        return True, "queued"

    memory_mod = types.ModuleType("api.db.services.memory_service")
    memory_mod.MemoryService = FakeMemoryService
    joint_mod = types.ModuleType("api.db.joint_services.memory_message_service")
    joint_mod.queue_save_to_memory_task = fake_queue
    monkeypatch.setitem(sys.modules, "api.db.services.memory_service", memory_mod)
    monkeypatch.setitem(sys.modules, "api.db.joint_services.memory_message_service", joint_mod)
    monkeypatch.setenv("OMNIRAG_AGENT_MEMORY_WRITE", "1")
    monkeypatch.delenv("OMNIRAG_AGENT_ALLOW_SEMANTIC_MEMORY_WRITE", raising=False)

    ok, _ = asyncio.run(
        persist_strategy_memory(
            ["mine", "other", "semantic"],
            tenant_id="tenant-a",
            user_id="u",
            agent_id="a",
            session_id="s",
            strategy_record="Agent task strategy record. Final governance action: accept.",
        )
    )
    assert ok is True
    assert captured["ids"] == ["mine"]
    assert "secret factual answer" not in captured["message"]["user_input"].lower()
    assert "strategy-memory event" in captured["message"]["user_input"]
