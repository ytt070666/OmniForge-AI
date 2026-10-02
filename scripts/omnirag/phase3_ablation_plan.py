#!/usr/bin/env python3
"""Print the Phase-3 ablation matrix in execution order."""

ROWS = [
    ("P1", "Upstream RAGFlow text retrieval", "MM=0, Verifier=0"),
    ("P2", "Phase-2 adaptive text retrieval", "Adaptive=1, MM=0, Verifier=0"),
    ("P3-A", "Visual retrieval only benchmark", "Visual index + joint encoder"),
    ("P3-B", "Text + visual weighted RRF", "MM=1, Verifier=0"),
    ("P3-C", "Text + visual + agreement bonus", "MM=1, bonus>0, Verifier=0"),
    ("P3-D", "P3-C + deterministic evidence verifier", "MM=1, Verifier=1"),
    ("P3-E", "P3-D + reranker", "Reranker=1; run only after clean P3-D"),
]

print("Phase 3 ablation plan")
print("=" * 92)
for code, name, flags in ROWS:
    print(f"{code:6} | {name:48} | {flags}")
