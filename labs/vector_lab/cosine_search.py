from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class VectorRecord:
    id: str
    vector: tuple[float, ...]
    text: str = ""


def cosine(a: Iterable[float], b: Iterable[float]) -> float:
    aa = tuple(float(x) for x in a)
    bb = tuple(float(x) for x in b)
    if len(aa) != len(bb) or not aa:
        raise ValueError("vectors must be non-empty and have equal dimensions")
    dot = sum(x * y for x, y in zip(aa, bb, strict=True))
    na = math.sqrt(sum(x * x for x in aa))
    nb = math.sqrt(sum(y * y for y in bb))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def top_k(query: Iterable[float], records: Iterable[VectorRecord], k: int = 5) -> list[tuple[float, VectorRecord]]:
    if k < 1:
        raise ValueError("k must be >= 1")
    rows = [(cosine(query, row.vector), row) for row in records]
    rows.sort(key=lambda x: (-x[0], x[1].id))
    return rows[:k]
