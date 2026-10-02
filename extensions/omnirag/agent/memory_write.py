"""Conservative experience-memory write proposals."""

from __future__ import annotations

from .types import AgentTrace


def build_experience_memory(trace: AgentTrace) -> str:
    """Summarize strategy, not answer facts, for later planning.

    The text intentionally excludes the final answer, retrieved evidence, and
    the literal critic retry query. RAGFlow's configured memory extractor may
    turn this into episodic or procedural memory without creating a second
    source of factual truth.
    """
    attempts = len(trace.attempts)
    retry_count = sum(1 for a in trace.attempts if a.critic.retry_query)
    parts = [
        f"Agent task strategy record. Planning mode: {trace.plan.mode.value}.",
        f"The task finished with action: {trace.terminal_action.value if trace.terminal_action else 'unknown'} after {attempts} attempt(s).",
    ]
    if retry_count:
        parts.append(f"A critic-directed evidence retry was needed {retry_count} time(s).")
        parts.append("Useful procedure: when the verifier or sufficient-context review reports a material gap, run one bounded follow-up retrieval focused only on the unresolved evidence before accepting the answer.")
    else:
        parts.append("The initial evidence pass satisfied the configured evidence gates; no critic retry was needed.")
    return " ".join(parts)
