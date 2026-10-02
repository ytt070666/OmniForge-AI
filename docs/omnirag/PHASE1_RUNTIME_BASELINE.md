# OmniRAG-Agent Phase 1 - Live Baseline Procedure

## Objective

Freeze a reproducible, untouched RAGFlow 0.27.2 retrieval baseline before modifying `rag/nlp/search.py`.

## Why this step exists

The first planned innovation is query-adaptive hybrid retrieval. RAGFlow currently accepts a fixed `vector_similarity_weight`; therefore we first measure how several fixed weights behave on lexical, semantic, cross-lingual, RAG, memory, MCP, and multimodal-bridge questions.

This creates evidence for the Phase-2 hypothesis instead of assuming that one fixed weight is always best.

## Important source-level finding for the Elasticsearch baseline

In `Dealer.search()`, the Elasticsearch candidate-acquisition path constructs a weighted-sum fusion expression with weights `0.001,1`, while the user-provided `vector_similarity_weight` is later applied again in `Dealer.retrieval()` through local reranking/fusion. The request weight also influences `min_match`, but it does not directly become the Elasticsearch candidate-fusion weights.

Therefore our Phase-2 design should eventually treat **candidate acquisition** and **final score fusion** as two separate decision points. The current Phase-1 sweep changes only the exposed request weight and leaves the upstream candidate behavior untouched.

## Runtime prerequisites

1. RAGFlow backend is reachable.
2. The dependency stack and task executor are running.
3. A default embedding model is configured for the tenant.
4. An HTTP API key has been created in RAGFlow.
5. A default chat model is only required when `--include-chat` is used.

The collector defaults to `http://127.0.0.1:9380/api/v1`. Override with `RAGFLOW_API_ROOT` if needed.

## Commands

```bash
export RAGFLOW_API_KEY="YOUR_RAGFLOW_API_KEY"
export RAGFLOW_API_ROOT="http://127.0.0.1:9380/api/v1"

python3 scripts/omnirag/phase1_collect_baseline.py --dry-run

python3 scripts/omnirag/phase1_collect_baseline.py
python3 scripts/omnirag/phase1_evaluate_baseline.py
```

After a default chat model is configured:

```bash
python3 scripts/omnirag/phase1_collect_baseline.py --include-chat --chat-limit 6
python3 scripts/omnirag/phase1_evaluate_baseline.py
```

For a one-command acceptance run:

```bash
export RAGFLOW_API_KEY="YOUR_RAGFLOW_API_KEY"
bash scripts/omnirag/phase1_acceptance.sh
```

## What the collector does

1. Calls system health/version/status endpoints.
2. Creates a timestamped dataset.
3. Uploads the deterministic Phase-1 corpus.
4. Starts parsing and waits for every document to reach `DONE`.
5. Runs every benchmark question at vector weights `0.0, 0.3, 0.5, 0.7, 1.0`.
6. Captures overall, term, and vector similarity scores for returned chunks.
7. Captures client-side retrieval latency.
8. Optionally runs non-streaming chat completion samples.
9. Writes an immutable run manifest containing corpus hashes and baseline version information.

## Expected output

Each run is placed under:

```text
benchmarks/omnirag/phase1/results/<timestamp>/
```

Key files:

```text
run_manifest.json
retrieval_results.jsonl
retrieval_summary.json
BASELINE_REPORT.md
chat_results.jsonl     # only with --include-chat
```

## Acceptance criteria

Phase 1 is accepted only when all of the following are true:

- RAGFlow API ping succeeds.
- Six deterministic corpus files upload successfully.
- All six documents reach parse state `DONE`.
- 28 questions complete for all five fixed vector weights (140 retrieval calls).
- `retrieval_results.jsonl` contains similarity, vector similarity, and term similarity where the backend exposes them.
- `BASELINE_REPORT.md` is generated.
- `run_manifest.json` identifies RAGFlow 0.27.2 and archive commit `a024bea0cd93f39e6652a42bf84dd20c55bc560b`.
- No core retrieval source has been modified.

Only after these conditions pass do we create the Phase-2 feature branch for adaptive retrieval.
