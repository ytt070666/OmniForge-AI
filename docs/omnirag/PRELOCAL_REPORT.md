# OmniRAG-Agent pre-local preparation report

Date: 2026-09-12  
Upstream: RAGFlow 0.27.2  
Archive commit: `a024bea0cd93f39e6652a42bf84dd20c55bc560b`

## Status

The repository is now prepared for the first local runtime session, but no claim is made that RAGFlow has been started in this environment. The frozen baseline core is still untouched.

### Completed offline

- Frozen RAGFlow version and core hashes.
- Deterministic 28-query / 6-document retrieval baseline and fixed-weight sweep collector.
- Retrieval evaluator: Recall@K, MRR, NDCG@K, latency and score statistics.
- Deterministic generation grounding evaluator.
- Hardware-independent runtime and model profiles.
- Safe environment overlay templates with no committed secrets.
- Preview-only local environment configurator.
- Phase-2 query feature extractor and transparent adaptive policy.
- Independent candidate-stage and final-stage adaptive weights.
- Phase-2 patch for `rag/nlp/search.py`, guarded by the exact baseline SHA-256.
- Offline policy preview and future baseline replay tool.
- Phase-2 live collector, evaluator and ablation command generator.
- Evidence-verifier data interfaces reserved for the next phase.

## Selected first-run architecture

- API runtime: Python.
- Document engine: Elasticsearch.
- Metadata: MySQL.
- Object storage: MinIO.
- Cache: Redis.
- Queue: NATS.
- Embedding baseline: `Qwen/Qwen3-Embedding-0.6B` through bundled TEI.
- Chat/Vision target: `Qwen/Qwen3-VL-8B-Instruct` through an OpenAI-compatible endpoint.
- Reranker: off for Baseline-A; `Qwen/Qwen3-Reranker-0.6B` for a separate Baseline-B.
- DeepDoc: CPU for the first baseline.

## Phase-2 implementation prepared but not applied

The proposed method is a two-stage adaptive hybrid retrieval policy:

1. Candidate acquisition weight `w_c(q)`.
2. Final sparse/dense fusion weight `w_f(q)`.

The initial routes are lexical precision, hybrid, semantic, cross-lingual semantic and visual/mixed. Their initial weights are hypotheses that will be calibrated only after the untouched baseline has been collected.

## Validation performed in the preparation environment

- Python compile validation: PASS.
- Shell syntax validation: PASS.
- Frontend package manifest validation: PASS.
- RAGFlow version validation: PASS (`0.27.2`).
- Benchmark integrity: PASS (28 queries, 6 corpus files).
- OmniRAG config validation: PASS (3 model profiles, 2 runtime profiles).
- Adaptive policy preview: PASS.
- Phase-2 patch dry-run: PASS.
- Frozen core integrity: PASS (8 protected files unchanged).
- Adaptive policy unit tests: PASS (5/5).

Frozen `rag/nlp/search.py` SHA-256 remains:

`e11c2aa749db1a44d0698f3cdda9b85c0519a5919e05d173fec793dfca3b9387`

## Do not do yet

Do not apply `phase2_adaptive_retrieval.patch` before the local Phase-1 baseline is collected and archived. Do not enable evidence verification, memory policy changes, MCP extensions or other innovations in the baseline run. This preserves a defensible ablation chain.

## First local session, later

When local execution begins, follow `LOCAL_RUNBOOK_LATER.md` and `artifacts/omnirag/prelocal/LOCAL_RUN_COMMANDS.txt`. The first goal is not feature development; it is to produce the immutable original RAGFlow baseline report. Only then should Phase 2 be enabled.
