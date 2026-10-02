"""Conservative critic that combines RAGFlow and OmniRAG evidence signals."""

from __future__ import annotations

from .reflection import ReflectionQueryV1
from .types import AgentAction, CriticDecision

_INSUFFICIENT = {"UNANSWERABLE", "INSUFFICIENT", "CONFLICTING", "USEFUL_BUT_INCOMPLETE"}


def _unsupported_claims(verification: dict) -> tuple[str, ...]:
    out: list[str] = []
    for row in verification.get("claims") or []:
        if not isinstance(row, dict):
            continue
        if not row.get("supported") or row.get("conflict"):
            claim = str(row.get("claim") or "").strip()
            if claim and claim not in out:
                out.append(claim)
    return tuple(out[:4])


def _conflicting_claims(verification: dict) -> tuple[str, ...]:
    out = []
    for row in verification.get("claims") or []:
        if isinstance(row, dict) and row.get("conflict"):
            claim = str(row.get("claim") or "").strip()
            if claim and claim not in out:
                out.append(claim)
    return tuple(out[:4])


class EvidenceCriticV1:
    """Make one explicit terminal or retry decision.

    Decision precedence:
    1. empty answer is never accepted;
    2. deterministic conflicts / low support trigger another evidence pass while
       budget remains, otherwise abstention;
    3. RAGFlow SCA insufficiency receives the same bounded treatment;
    4. only then is the answer accepted.

    This preserves RAGFlow's strong native SCA signal while adding the Phase-3
    post-generation verifier as an independent safety gate.
    """

    name = "evidence_critic_v1"

    def __init__(self, reflector: ReflectionQueryV1 | None = None):
        self.reflector = reflector or ReflectionQueryV1()

    def decide(
        self,
        *,
        original_query: str,
        answer: str,
        verification: dict | None,
        rag_verdict: dict | None,
        retries_used: int,
        retry_budget: int,
    ) -> CriticDecision:
        verification = verification or {}
        rag_verdict = rag_verdict or {}
        retries_left = max(0, int(retry_budget) - int(retries_used))

        verifier_enabled = bool(verification.get("enabled"))
        verifier_decision = str(verification.get("decision") or "disabled").lower()
        verifier_conf = float(verification.get("confidence", 1.0 if not verifier_enabled else 0.0) or 0.0)
        rag_status = str(rag_verdict.get("status") or "").upper()
        rag_conf_raw = rag_verdict.get("agent_confidence")
        rag_conf = float(rag_conf_raw) if isinstance(rag_conf_raw, (int, float)) else None

        missing = list(_unsupported_claims(verification))
        missing.extend(str(x).strip() for x in (rag_verdict.get("missing_claims") or []) if str(x).strip())
        missing = list(dict.fromkeys(missing))[:4]
        conflicts = list(_conflicting_claims(verification))
        if rag_status == "CONFLICTING":
            hard = [str(x).strip() for x in (rag_verdict.get("hard_violations") or []) if str(x).strip()]
            conflicts.extend(hard)
        conflicts = list(dict.fromkeys(conflicts))[:4]
        feedback = str(rag_verdict.get("feedback") or "")

        if not (answer or "").strip():
            if retries_left:
                retry_query = self.reflector.build(original_query, missing_targets=tuple(missing), feedback="No usable answer was generated.")
                return CriticDecision(AgentAction.RETRIEVE_MORE, "empty answer; retry with evidence", 0.0, tuple(missing), tuple(conflicts), retry_query)
            return CriticDecision(AgentAction.ABSTAIN, "empty answer and retry budget exhausted", 0.0, tuple(missing), tuple(conflicts))

        verifier_needs_work = verifier_enabled and verifier_decision in {"retrieve_more", "abstain"}
        rag_needs_work = rag_status in _INSUFFICIENT
        if verifier_needs_work or rag_needs_work:
            reasons = []
            if verifier_needs_work:
                reasons.append(f"evidence verifier={verifier_decision}")
            if rag_needs_work:
                reasons.append(f"RAGFlow SCA={rag_status}")
            confidence_candidates = [verifier_conf] if verifier_enabled else []
            if rag_conf is not None:
                confidence_candidates.append(rag_conf)
            confidence = min(confidence_candidates) if confidence_candidates else 0.0

            if retries_left:
                retry_query = self.reflector.build(
                    original_query,
                    missing_targets=tuple(missing),
                    conflicts=tuple(conflicts),
                    feedback=feedback,
                )
                return CriticDecision(
                    AgentAction.RETRIEVE_MORE,
                    "; ".join(reasons),
                    confidence,
                    tuple(missing),
                    tuple(conflicts),
                    retry_query,
                )
            return CriticDecision(
                AgentAction.ABSTAIN,
                "; ".join(reasons) + "; retry budget exhausted",
                confidence,
                tuple(missing),
                tuple(conflicts),
            )

        confidence_candidates = []
        if verifier_enabled:
            confidence_candidates.append(verifier_conf)
        if rag_conf is not None:
            confidence_candidates.append(rag_conf)
        confidence = min(confidence_candidates) if confidence_candidates else 1.0
        return CriticDecision(AgentAction.ACCEPT, "evidence gates passed", confidence, tuple(missing), tuple(conflicts))
