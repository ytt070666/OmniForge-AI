"""Stable data contracts for multimodal retrieval."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class VisualRecord:
    """A persisted visual chunk and its joint text-image embedding."""

    chunk_id: str
    dataset_id: str
    document_id: str
    document_name: str
    image_id: str
    content: str
    vector: tuple[float, ...]
    doc_type: str = "image"
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VisualHit:
    """One visual-index retrieval result."""

    record: VisualRecord
    score: float
    rank: int

    def as_dict(self) -> dict[str, Any]:
        data = self.record.as_dict()
        data.update({"visual_score": float(self.score), "visual_rank": int(self.rank)})
        return data


@dataclass(frozen=True)
class FusedCandidate:
    """Auditable result of text/visual rank fusion."""

    chunk_id: str
    fused_score: float
    text_rank: int | None
    visual_rank: int | None
    text_score: float | None
    visual_score: float | None
    agreement: bool
    chunk: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["chunk"] = dict(self.chunk)
        return d
