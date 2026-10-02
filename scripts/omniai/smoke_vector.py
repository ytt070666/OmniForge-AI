"""Small deterministic checks for the exact vector search implementation."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from labs.vector_lab.cosine_search import VectorRecord, cosine, top_k


def main() -> None:
    assert cosine((1, 0), (1, 0)) == 1.0
    assert cosine((1, 0), (0, 1)) == 0.0
    rows = [
        VectorRecord("gateway", (1, 0), "GW-01"),
        VectorRecord("database", (0, 1), "DB-01"),
    ]
    ranked = top_k((0.9, 0.1), rows, 2)
    assert [record.id for _, record in ranked] == ["gateway", "database"]
    assert ranked[0][1].text == "GW-01"
    try:
        cosine((1, 0), (1, 0, 0))
    except ValueError:
        pass
    else:
        raise AssertionError("dimension mismatch must be rejected")
    print("cosine, exact top-k, metadata, dimension: PASS")


if __name__ == "__main__":
    main()
