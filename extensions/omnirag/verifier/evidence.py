"""Evidence-verification interfaces reserved for the post-retrieval phase.

This file intentionally provides stable data structures without altering answer
generation yet. The verifier will be enabled only after retrieval experiments
are complete, preventing multiple innovations from contaminating one ablation.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    source: str
    content: str
    modality: str = "text"
    retrieval_score: float = 0.0


@dataclass(frozen=True)
class ClaimVerification:
    claim: str
    supported: bool
    support_score: float
    evidence_ids: tuple[str, ...]
    conflict: bool = False
    note: str = ""

    def as_dict(self) -> dict:
        return asdict(self)
