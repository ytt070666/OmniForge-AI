# Pre-local gate

This document defines what must be finished before the repository is moved to the local GPU/server.

## Gate A — upstream baseline remains pristine

`rag/nlp/search.py` and the other eight protected core files must still match `BASELINE_CORE_HASHES.json`. The adaptive patch is prepared but **not applied**.

## Gate B — runtime is fixed

Phase 1 uses:

- RAGFlow 0.27.2
- Python API path (`API_PROXY_SCHEME=python`)
- Elasticsearch
- MySQL
- MinIO
- Redis
- NATS
- TEI with `Qwen/Qwen3-Embedding-0.6B`
- DeepDoc CPU

## Gate C — model integration is parameterized

No local hardware assumption is embedded into the source. Chat/Vision and reranker endpoints are supplied later through environment variables. This lets the same repository run with local vLLM or a temporary OpenAI-compatible API.

## Gate D — Phase 2 is already coded but isolated

The repository contains:

- deterministic query feature extraction;
- `HeuristicPolicyV1`;
- separate candidate-stage and final-stage vector weights;
- an integration boundary controlled by `OMNIRAG_ADAPTIVE_RETRIEVAL`;
- a source patch that is validated against the exact frozen RAGFlow hash;
- offline policy preview and baseline replay tools.

The patch may only be applied after the live Phase-1 report is archived.

## Gate E — required local execution order

1. Run environment check.
2. Start upstream baseline with adaptive flags off.
3. Configure embedding and chat/vision endpoints.
4. Run smoke test.
5. Run 140 fixed-weight retrieval cases.
6. Archive the run manifest and report.
7. Optionally collect reranker baseline as a separate experiment.
8. Apply the Phase-2 patch.
9. Enable adaptive retrieval.
10. Run candidate-only, final-only and two-stage adaptive ablations.

This order prevents leakage between baseline and proposed method.
