"""Small persistent visual sidecar index used by Phase-3 research experiments.

The production integration is deliberately backend-agnostic. Phase 3 ships a
JSONL cosine index because it is inspectable and reproducible for a thesis
benchmark; a Milvus/ES adapter can replace it behind the same interface later.
"""

from __future__ import annotations

import json
import math
import os
import tempfile
from pathlib import Path
from typing import Iterable

from .types import VisualHit, VisualRecord


def _normalize(vector: Iterable[float]) -> tuple[float, ...]:
    vec = tuple(float(x) for x in vector)
    norm = math.sqrt(sum(x * x for x in vec))
    if norm <= 0:
        raise ValueError("visual embedding must have non-zero norm")
    return tuple(x / norm for x in vec)


def _dot(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    if len(a) != len(b):
        raise ValueError(f"vector dimension mismatch: {len(a)} != {len(b)}")
    return float(sum(x * y for x, y in zip(a, b)))


class JsonlVisualIndex:
    def __init__(self, path: str | os.PathLike[str]):
        self.path = Path(path)
        self._records: list[VisualRecord] | None = None
        self._dim: int | None = None

    @property
    def dim(self) -> int | None:
        self._ensure_loaded()
        return self._dim

    def _ensure_loaded(self) -> None:
        if self._records is not None:
            return
        records: list[VisualRecord] = []
        dim: int | None = None
        if self.path.exists():
            with self.path.open("r", encoding="utf-8") as f:
                for line_no, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    raw = json.loads(line)
                    vec = _normalize(raw.pop("vector"))
                    if dim is None:
                        dim = len(vec)
                    elif len(vec) != dim:
                        raise ValueError(f"mixed vector dimensions in {self.path} at line {line_no}")
                    raw["vector"] = vec
                    raw["metadata"] = raw.get("metadata") or {}
                    records.append(VisualRecord(**raw))
        self._records = records
        self._dim = dim

    def records(self) -> tuple[VisualRecord, ...]:
        self._ensure_loaded()
        return tuple(self._records or [])

    def replace(self, records: Iterable[VisualRecord]) -> None:
        normalized: list[VisualRecord] = []
        dim: int | None = None
        for rec in records:
            vec = _normalize(rec.vector)
            if dim is None:
                dim = len(vec)
            elif len(vec) != dim:
                raise ValueError("all visual index records must share one vector dimension")
            normalized.append(
                VisualRecord(
                    chunk_id=rec.chunk_id,
                    dataset_id=rec.dataset_id,
                    document_id=rec.document_id,
                    document_name=rec.document_name,
                    image_id=rec.image_id,
                    content=rec.content,
                    vector=vec,
                    doc_type=rec.doc_type,
                    metadata=dict(rec.metadata),
                )
            )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=self.path.name + ".", suffix=".tmp", dir=str(self.path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                for rec in normalized:
                    f.write(json.dumps(rec.as_dict(), ensure_ascii=False, sort_keys=True) + "\n")
            os.replace(tmp_name, self.path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
        self._records = normalized
        self._dim = dim

    def search(
        self,
        query_vector: Iterable[float],
        top_k: int = 10,
        dataset_ids: set[str] | None = None,
        document_ids: set[str] | None = None,
    ) -> list[VisualHit]:
        self._ensure_loaded()
        q = _normalize(query_vector)
        if self._dim is not None and len(q) != self._dim:
            raise ValueError(f"query vector dimension {len(q)} != index dimension {self._dim}")
        scored: list[tuple[float, VisualRecord]] = []
        for rec in self._records or []:
            if dataset_ids and rec.dataset_id not in dataset_ids:
                continue
            if document_ids and rec.document_id not in document_ids:
                continue
            scored.append((_dot(q, rec.vector), rec))
        scored.sort(key=lambda item: (-item[0], item[1].chunk_id))
        return [VisualHit(record=rec, score=score, rank=i) for i, (score, rec) in enumerate(scored[: max(0, int(top_k))], start=1)]
