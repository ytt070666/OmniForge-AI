# Phase 2 — Query-Adaptive Two-Stage Hybrid Retrieval

## Research question

RAGFlow 0.27.2 exposes a user-facing `vector_similarity_weight`, but on the Elasticsearch path its candidate acquisition uses a dense-dominant weighted-sum (`0.001,1`) before the later local term/vector fusion. A single fixed setting therefore cannot represent the needs of exact identifiers, semantic paraphrases, cross-lingual queries and future visual queries equally well.

## Proposed method

For a query `q`, extract transparent features `x(q)` and predict two independent weights:

- candidate-stage vector weight: `w_c = f_c(x(q))`
- final-stage vector weight: `w_f = f_f(x(q))`

The first implementation is deterministic (`HeuristicPolicyV1`) so every decision can be inspected and reproduced. A learned router can later replace the policy behind the same interface.

### Initial routes

| Route | Candidate vector weight | Final vector weight | Intent |
|---|---:|---:|---|
| lexical_precision | 0.35 | 0.22 | codes, ports, IDs, quoted exact phrases |
| hybrid | 0.58 | 0.52 | no dominant signal |
| semantic | 0.72 | 0.70 | paraphrase/explanation questions |
| crosslingual_semantic | 0.85 | 0.82 | CJK query where lexical overlap may be weak |
| visual_or_mixed | 0.78 | 0.72 | figure/chart/image/table/topology signals |

These are **initial hypotheses**, not final paper results. Phase-1 fixed-weight data and later grid search will calibrate them.

## Ablation matrix

1. Upstream RAGFlow fixed baseline.
2. Adaptive final fusion only (`candidate=off`, `final=on`).
3. Adaptive candidate acquisition only (`candidate=on`, `final=off`).
4. Full two-stage adaptive policy (`candidate=on`, `final=on`).
5. Full two-stage + reranker.

Report Recall@1/3/5/10, MRR, NDCG@5, mean latency and candidate count. Generation metrics are kept separate so retriever gains are not confused with LLM quality.

## Safety / reproducibility guard

`phase2_apply_patch.py` checks the SHA-256 of the frozen `rag/nlp/search.py` before it changes anything. The patch is never applied automatically by Phase-1 scripts.
