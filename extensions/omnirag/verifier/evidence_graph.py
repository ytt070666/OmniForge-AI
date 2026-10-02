"""Deterministic claim-evidence graph used before adding an LLM judge."""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from typing import Iterable

from .evidence import ClaimVerification, EvidenceItem

_SENTENCE_RE = re.compile(r"(?<=[.!?。！？；;])\s+|\n+")
_TOKEN_RE = re.compile(r"[A-Za-z0-9_./:-]+|[\u3400-\u9fff]")
_NUM_RE = re.compile(r"[-+]?\d+(?:\.\d+)?%?")
_NEGATIONS = {"not", "no", "never", "without", "不是", "没有", "未", "无", "不"}


def _tokens(text: str) -> set[str]:
    return {m.group(0).lower() for m in _TOKEN_RE.finditer(text or "") if len(m.group(0).strip()) > 0}


def _numbers(text: str) -> set[str]:
    return {m.group(0) for m in _NUM_RE.finditer(text or "")}


def _has_negation(text: str) -> bool:
    lower = (text or "").lower()
    return any(n in lower for n in _NEGATIONS)


def split_claims(answer: str) -> list[str]:
    claims = [x.strip(" \t-*#") for x in _SENTENCE_RE.split(answer or "")]
    return [c for c in claims if len(c) >= 3]


def support_score(claim: str, evidence: str) -> float:
    ct = _tokens(claim)
    et = _tokens(evidence)
    if not ct:
        return 0.0
    overlap = len(ct & et) / max(1, len(ct))
    nums = _numbers(claim)
    num_support = 1.0 if not nums else len(nums & _numbers(evidence)) / len(nums)
    # Numeric claims should not be marked strongly supported by lexical overlap
    # when their values are absent from evidence.
    score = 0.72 * overlap + 0.28 * num_support
    return max(0.0, min(1.0, score))


def likely_conflict(claim: str, evidence: str) -> bool:
    nums = _numbers(claim)
    ev_nums = _numbers(evidence)
    numeric_conflict = bool(
        nums
        and ev_nums
        and (nums - ev_nums)
        and (ev_nums - nums)
        and len(_tokens(claim) & _tokens(evidence)) >= 2
    )
    negation_conflict = _has_negation(claim) != _has_negation(evidence) and len(_tokens(claim) & _tokens(evidence)) >= 3
    return numeric_conflict or negation_conflict


@dataclass(frozen=True)
class VerificationReport:
    confidence: float
    supported_claim_ratio: float
    modality_coverage: float
    conflict_count: int
    decision: str
    claims: tuple[ClaimVerification, ...]
    evidence_count: int

    def as_dict(self) -> dict:
        d = asdict(self)
        d["claims"] = [c.as_dict() for c in self.claims]
        return d


def verify_claims(
    answer: str,
    evidence: Iterable[EvidenceItem],
    support_threshold: float = 0.42,
    pass_threshold: float = 0.62,
    abstain_threshold: float = 0.34,
) -> VerificationReport:
    ev = list(evidence)
    claims = split_claims(answer)
    if not claims:
        return VerificationReport(0.0, 0.0, 0.0, 0, "abstain", tuple(), len(ev))

    verified: list[ClaimVerification] = []
    modalities_used: set[str] = set()
    conflicts = 0
    for claim in claims:
        scored = sorted(((support_score(claim, item.content), item) for item in ev), key=lambda x: (-x[0], x[1].evidence_id))
        best_score = scored[0][0] if scored else 0.0
        supporting = tuple(item.evidence_id for score, item in scored[:3] if score >= support_threshold)
        conflict = any(likely_conflict(claim, item.content) for _, item in scored[:5])
        if conflict:
            conflicts += 1
        for score, item in scored[:3]:
            if score >= support_threshold:
                modalities_used.add(item.modality)
        verified.append(
            ClaimVerification(
                claim=claim,
                supported=bool(supporting) and not conflict,
                support_score=best_score,
                evidence_ids=supporting,
                conflict=conflict,
                note="deterministic lexical/numeric verifier; semantic judge can be layered later",
            )
        )

    supported_ratio = sum(1 for x in verified if x.supported) / len(verified)
    available_modalities = {item.modality for item in ev if item.modality}
    modality_coverage = len(modalities_used) / max(1, len(available_modalities))
    avg_support = sum(x.support_score for x in verified) / len(verified)
    conflict_penalty = min(0.35, conflicts * 0.12)
    confidence = max(0.0, min(1.0, 0.55 * supported_ratio + 0.30 * avg_support + 0.15 * modality_coverage - conflict_penalty))

    if conflicts > 0 or confidence < abstain_threshold:
        decision = "abstain"
    elif confidence < pass_threshold:
        decision = "retrieve_more"
    else:
        decision = "pass"
    return VerificationReport(confidence, supported_ratio, modality_coverage, conflicts, decision, tuple(verified), len(ev))
