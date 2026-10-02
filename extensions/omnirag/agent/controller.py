"""Bounded state machine for memory-aware evidence-governed research."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable, Iterable
from typing import Any

from .critic import EvidenceCriticV1
from .memory_policy import render_planning_memory_context, select_planning_memories
from .memory_write import build_experience_memory
from .planner import PlanningPolicyV1
from .reflection import query_signature
from .types import AgentAction, AgentRunResult, AgentTrace, AttemptRecord

ResearchCallback = Callable[..., Awaitable[dict[str, Any]]]
VerifyCallback = Callable[[str, list[dict]], Awaitable[dict[str, Any]] | dict[str, Any]]
RecallCallback = Callable[[str], Awaitable[Iterable[dict]] | Iterable[dict]]
PersistCallback = Callable[[str], Awaitable[Any] | Any]


async def _maybe_await(value):
    if inspect.isawaitable(value):
        return await value
    return value


class MemoryAwareAgentController:
    """Explicit finite-state controller with a hard retry budget.

    This controller is deliberately small: RAGFlow owns actual planning,
    retrieval, tool execution, and answer composition. OmniRAG owns only the
    governance transitions around those capabilities.
    """

    name = "memory_aware_agent_controller_v1"

    def __init__(self, planner: PlanningPolicyV1 | None = None, critic: EvidenceCriticV1 | None = None):
        self.planner = planner or PlanningPolicyV1()
        self.critic = critic or EvidenceCriticV1()

    async def run(
        self,
        query: str,
        *,
        research: ResearchCallback,
        verify: VerifyCallback | None = None,
        recall: RecallCallback | None = None,
        persist: PersistCallback | None = None,
        memory_top_n: int = 5,
    ) -> AgentRunResult:
        plan = self.planner.decide(query)
        memory_items = []
        memory_context = ""
        if recall is not None and plan.use_long_term_memory:
            rows = list(await _maybe_await(recall(query)) or [])
            memory_items = select_planning_memories(
                query,
                rows,
                allowed_types=plan.allowed_memory_types,
                top_n=memory_top_n,
            )
            memory_context = render_planning_memory_context(memory_items)

        trace = AgentTrace(original_query=query, plan=plan, memory_items=memory_items)
        current_query = query
        seen_signatures: set[str] = set()
        final_answer = ""
        final_reference: dict[str, Any] = {}
        final_metadata: dict[str, Any] = {}

        max_attempts = max(1, plan.retry_budget + 1)
        for attempt in range(1, max_attempts + 1):
            sig = query_signature(current_query)
            if sig in seen_signatures:
                trace.terminal_action = AgentAction.ABSTAIN
                trace.termination_reason = "reflection loop guard: repeated query signature"
                return AgentRunResult(final_answer, AgentAction.ABSTAIN, trace, current_query, final_reference, final_metadata)
            seen_signatures.add(sig)

            outcome = await research(
                current_query,
                original_query=query,
                planning_memory=memory_context,
                attempt=attempt,
                max_attempts=max_attempts,
            )
            outcome = outcome or {}
            answer = str(outcome.get("answer") or "")
            chunks = list(outcome.get("chunks") or [])
            rag_verdict = dict(outcome.get("rag_verdict") or {})
            verification = dict(outcome.get("verification") or {})
            if not verification and verify is not None:
                verification = dict(await _maybe_await(verify(answer, chunks)) or {})

            critic = self.critic.decide(
                original_query=query,
                answer=answer,
                verification=verification,
                rag_verdict=rag_verdict,
                retries_used=attempt - 1,
                retry_budget=plan.retry_budget,
            )
            trace.attempts.append(
                AttemptRecord(
                    attempt=attempt,
                    query=current_query,
                    answer=answer,
                    verification=verification,
                    rag_verdict=rag_verdict,
                    critic=critic,
                    retrieved_chunk_ids=tuple(str(c.get("chunk_id") or c.get("id") or "") for c in chunks if isinstance(c, dict)),
                )
            )
            final_answer = answer
            final_reference = dict(outcome.get("reference") or {})
            final_metadata = dict(outcome.get("metadata") or {})

            if critic.action == AgentAction.ACCEPT:
                trace.terminal_action = AgentAction.ACCEPT
                trace.termination_reason = critic.reason
                if persist is not None:
                    await _maybe_await(persist(build_experience_memory(trace)))
                return AgentRunResult(final_answer, AgentAction.ACCEPT, trace, current_query, final_reference, final_metadata)

            if critic.action == AgentAction.ABSTAIN:
                trace.terminal_action = AgentAction.ABSTAIN
                trace.termination_reason = critic.reason
                return AgentRunResult(final_answer, AgentAction.ABSTAIN, trace, current_query, final_reference, final_metadata)

            next_query = critic.retry_query.strip()
            if not next_query:
                trace.terminal_action = AgentAction.ABSTAIN
                trace.termination_reason = "critic requested retrieval but produced no bounded follow-up query"
                return AgentRunResult(final_answer, AgentAction.ABSTAIN, trace, current_query, final_reference, final_metadata)
            current_query = next_query

        trace.terminal_action = AgentAction.ABSTAIN
        trace.termination_reason = "retry budget exhausted"
        return AgentRunResult(final_answer, AgentAction.ABSTAIN, trace, current_query, final_reference, final_metadata)
