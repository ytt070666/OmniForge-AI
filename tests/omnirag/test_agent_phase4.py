import asyncio

from extensions.omnirag.agent.controller import MemoryAwareAgentController
from extensions.omnirag.agent.critic import EvidenceCriticV1
from extensions.omnirag.agent.planner import PlanningPolicyV1
from extensions.omnirag.agent.ragflow_governance import merge_critic_into_rag_verdict
from extensions.omnirag.agent.types import AgentAction


def verification(decision="pass", confidence=0.8, conflict=False):
    return {
        "enabled": True,
        "decision": decision,
        "confidence": confidence,
        "claims": [
            {
                "claim": "Latency is 42 ms.",
                "supported": decision == "pass" and not conflict,
                "conflict": conflict,
            }
        ],
    }


def test_planner_uses_existing_ragflow_planner_with_visual_governance():
    d = PlanningPolicyV1().decide("What does the latency chart show?")
    assert d.requires_visual is True
    assert d.retry_budget == 2
    assert d.allowed_memory_types == ("procedural", "episodic")


def test_critic_accepts_when_both_gates_pass():
    c = EvidenceCriticV1().decide(
        original_query="q",
        answer="supported answer",
        verification=verification(),
        rag_verdict={"status": "SUFFICIENT", "agent_confidence": 0.9},
        retries_used=0,
        retry_budget=2,
    )
    assert c.action == AgentAction.ACCEPT


def test_critic_requests_bounded_retry_on_verifier_gap():
    c = EvidenceCriticV1().decide(
        original_query="What is the latency?",
        answer="Latency is 42 ms.",
        verification=verification("retrieve_more", 0.5),
        rag_verdict={"status": "SUFFICIENT"},
        retries_used=0,
        retry_budget=1,
    )
    assert c.action == AgentAction.RETRIEVE_MORE
    assert "original question" in c.retry_query.lower()
    assert "Latency is 42 ms" in c.retry_query


def test_critic_abstains_when_conflict_and_budget_exhausted():
    c = EvidenceCriticV1().decide(
        original_query="What is the latency?",
        answer="Latency is 42 ms.",
        verification=verification("abstain", 0.2, conflict=True),
        rag_verdict={"status": "CONFLICTING"},
        retries_used=1,
        retry_budget=1,
    )
    assert c.action == AgentAction.ABSTAIN


def test_merge_critic_uses_native_ragflow_insufficiency_contract():
    gov = {
        "enabled": True,
        "action": "retrieve_more",
        "critic": {"missing_targets": ["exact latency"], "retry_query": "Find direct latency evidence", "reason": "verifier gap"},
    }
    out = merge_critic_into_rag_verdict({"status": "SUFFICIENT"}, gov)
    assert out["status"] == "INSUFFICIENT"
    assert "Find direct latency evidence" in out["missing_claims"]
    assert "OmniRAG critic" in out["feedback"]


def test_controller_retries_then_accepts_and_persists_strategy_only():
    calls = []
    persisted = []

    async def research(query, **kwargs):
        calls.append(query)
        if len(calls) == 1:
            return {
                "answer": "Latency is 42 ms.",
                "chunks": [{"chunk_id": "a"}],
                "verification": verification("retrieve_more", 0.5),
                "rag_verdict": {"status": "INSUFFICIENT", "missing_claims": ["direct latency evidence"]},
            }
        return {
            "answer": "Latency is 42 ms.",
            "chunks": [{"chunk_id": "b"}],
            "verification": verification("pass", 0.9),
            "rag_verdict": {"status": "SUFFICIENT", "agent_confidence": 0.9},
        }

    async def persist(text):
        persisted.append(text)

    result = asyncio.run(MemoryAwareAgentController().run("What is the latency?", research=research, persist=persist))
    assert result.action == AgentAction.ACCEPT
    assert len(calls) == 2
    assert len(result.trace.attempts) == 2
    assert len(persisted) == 1
    assert "Latency is 42 ms" not in persisted[0]
    assert "strategy" in persisted[0].lower()


def test_controller_never_persists_failed_run():
    persisted = []

    async def research(query, **kwargs):
        return {
            "answer": "",
            "chunks": [],
            "verification": {"enabled": True, "decision": "abstain", "confidence": 0.0, "claims": []},
            "rag_verdict": {"status": "UNANSWERABLE"},
        }

    result = asyncio.run(MemoryAwareAgentController().run("Simple fact?", research=research, persist=lambda x: persisted.append(x)))
    assert result.action == AgentAction.ABSTAIN
    assert persisted == []


def test_merge_critic_projects_terminal_abstention_to_native_verdict():
    gov = {
        "enabled": True,
        "action": "abstain",
        "critic": {"missing_targets": ["source evidence"], "retry_query": "", "reason": "retry budget exhausted"},
    }
    out = merge_critic_into_rag_verdict({"status": "SUFFICIENT"}, gov)
    assert out["status"] == "UNANSWERABLE"
    assert out["omnirag_action"] == "abstain"
    assert "OmniRAG critic" in out["feedback"]


def test_strategy_record_remembers_prior_retry_without_storing_retry_text():
    from extensions.omnirag.agent.ragflow_governance import strategy_record_from_governance

    history = [
        {"enabled": True, "action": "retrieve_more", "critic": {"retry_query": "Find SECRET-42", "reason": "evidence verifier=retrieve_more"}},
        {"enabled": True, "action": "accept", "critic": {"reason": "evidence gates passed"}},
    ]
    record = strategy_record_from_governance(
        {"enabled": True, "action": "accept", "plan": {"mode": "research"}, "critic": {"reason": "evidence gates passed"}},
        history,
    )
    assert "follow-up retrieval" in record
    assert "SECRET-42" not in record
