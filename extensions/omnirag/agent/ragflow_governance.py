"""Feature-flagged governance helpers for RAGFlow's native agentic RAG.

RAGFlow 0.27.2 already owns the inner research planner, sufficient-context
review, query rewriting, and evidence collection. OmniRAG does not replace
those mechanisms. It adds a post-generation evidence gate and a deterministic,
bounded retry contract around the native graph.

A key implementation constraint is that ``rag`` is configured as a terminal
tool by ``dialog_service.rag_agent``. Therefore a retry request cannot safely
rely on a later outer-LLM tool-calling round. When governance is enabled the
RAGTools integration performs the bounded critic-directed retry *inside* the
terminal tool, before exposing the accepted answer to the client.
"""

from __future__ import annotations

import os

from extensions.omnirag.verifier.runtime import maybe_verify_answer

from .critic import EvidenceCriticV1
from .planner import PlanningPolicyV1


def _flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def governance_enabled() -> bool:
    return _flag("OMNIRAG_AGENT_GOVERNANCE", False)


def retry_budget_for_query(query: str) -> int:
    """Return the hard critic-directed retry budget for one terminal ``rag`` call.

    The environment override is clamped so a configuration typo cannot create
    an unbounded research loop. RAGFlow's *inner* graph has its own independent
    search/rewrite limits; this budget controls only additional post-generation
    verifier retries.
    """

    plan = PlanningPolicyV1().decide(query)
    raw = os.getenv("OMNIRAG_AGENT_RETRY_BUDGET")
    if raw is None:
        return plan.retry_budget
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return plan.retry_budget
    return max(0, min(value, 3))


def review_agentic_result(
    *,
    query: str,
    answer: str,
    chunks: list[dict],
    rag_verdict: dict | None,
    retries_used: int,
) -> dict:
    if not governance_enabled():
        return {"enabled": False, "action": "disabled"}

    plan = PlanningPolicyV1().decide(query)
    verification = maybe_verify_answer(answer, chunks)
    critic = EvidenceCriticV1().decide(
        original_query=query,
        answer=answer,
        verification=verification,
        rag_verdict=rag_verdict or {},
        retries_used=retries_used,
        retry_budget=retry_budget_for_query(query),
    )
    return {
        "enabled": True,
        "plan": plan.as_dict(),
        "verification": verification,
        "critic": critic.as_dict(),
        "action": critic.action.value,
        "retry_budget": retry_budget_for_query(query),
        "retries_used": max(0, int(retries_used)),
    }


def merge_critic_into_rag_verdict(rag_verdict: dict | None, governance: dict) -> dict:
    """Project the OmniRAG critic decision onto RAGFlow's native verdict shape.

    The projection is intentionally lossless for the native fields: existing
    missing claims and feedback are retained. ``retrieve_more`` maps to
    ``INSUFFICIENT``; terminal ``abstain`` maps to ``UNANSWERABLE`` unless the
    native verifier already reported ``CONFLICTING``. ``accept`` leaves the
    native verdict unchanged.
    """

    out = dict(rag_verdict or {})
    if not governance.get("enabled"):
        return out

    action = str(governance.get("action") or "")
    if action not in {"retrieve_more", "abstain"}:
        return out

    critic = governance.get("critic") or {}
    existing_missing = [str(x).strip() for x in out.get("missing_claims") or [] if str(x).strip()]
    extra_missing = [str(x).strip() for x in critic.get("missing_targets") or [] if str(x).strip()]
    retry_query = str(critic.get("retry_query") or "").strip()
    missing = existing_missing + extra_missing
    if action == "retrieve_more" and retry_query:
        missing.append(retry_query)

    if action == "retrieve_more":
        out["status"] = "INSUFFICIENT"
    elif str(out.get("status") or "").upper() != "CONFLICTING":
        out["status"] = "UNANSWERABLE"

    out["missing_claims"] = list(dict.fromkeys(missing))[:4]
    feedback = str(out.get("feedback") or "").strip()
    critic_reason = str(critic.get("reason") or "").strip()
    if critic_reason:
        marker = "OmniRAG critic: " + critic_reason
        out["feedback"] = (feedback + " | " if feedback else "") + marker
    out["omnirag_action"] = action
    return out


def retry_query_from_governance(governance: dict) -> str:
    if not governance.get("enabled") or governance.get("action") != "retrieve_more":
        return ""
    return str((governance.get("critic") or {}).get("retry_query") or "").strip()


def abstention_answer(empty_response: str = "") -> str:
    """Return a transparent terminal answer when evidence gates cannot pass."""

    if (empty_response or "").strip():
        return empty_response.strip()
    return "The available evidence is insufficient or conflicting, so I cannot provide a reliably supported answer from the current sources."


def strategy_record_from_governance(governance: dict, history: list[dict] | None = None) -> str:
    """Return a fact-free strategy record suitable for experience memory.

    ``history`` is optional so callers can record that an earlier critic pass
    required a retry even when the final governance action is ``accept``. No
    answer text, source content, entity value, or retry-query literal is stored.
    """

    if not governance.get("enabled"):
        return ""
    plan = governance.get("plan") or {}
    critic = governance.get("critic") or {}
    mode = str(plan.get("mode") or "unknown")
    action = str(governance.get("action") or "unknown")
    reason = str(critic.get("reason") or "")
    rounds = [x for x in (history or []) if isinstance(x, dict) and x.get("enabled")]
    retry_needed = any(str(x.get("action") or "") == "retrieve_more" for x in rounds) or action == "retrieve_more"
    parts = [f"Agent task strategy record. Planning mode: {mode}. Final governance action: {action}."]
    if retry_needed:
        parts.append("At least one evidence gate required a bounded follow-up retrieval before termination.")
    else:
        parts.append("The available evidence passed the configured governance gates without a critic-directed follow-up search.")
    if reason:
        # Critic reason strings contain gate/status names, not retrieved facts.
        parts.append("Governance signal: " + reason[:240])
    return " ".join(parts)
