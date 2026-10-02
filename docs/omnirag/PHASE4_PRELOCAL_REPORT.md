# OmniRAG-Agent Phase 4 pre-local report

## Status

Phase 4 is code-complete for the **offline/pre-local** scope. No live RAGFlow services, model endpoints, GPU workloads, or real memory store were started during this phase.

## What was implemented

- memory-aware governance extension under `extensions/omnirag/agent/`;
- safe procedural/episodic planning-memory selection;
- explicit rank-derived memory scoring (no fabricated raw similarity);
- tenant boundary enforcement for memory recall/write;
- conservative evidence critic combining RAGFlow SCA + Phase-3 verifier;
- deterministic reflection query builder;
- retry budget and loop guard;
- transparent terminal abstention;
- generic finite-state controller for deterministic unit testing;
- strategy-only memory consolidation after accepted runs;
- Phase-4 integration patch for `dialog_service.py` and `agentic_rag.py`;
- contract benchmark scenarios and validation tooling;
- local-run plan and feature-flag configuration.

## Important source correction

The reviewed RAGFlow tool loop treats `rag` as a terminal tool. Therefore the earlier concept of asking the *outer* model to call `rag` again is not a dependable retry mechanism in this path. Phase 4 now buffers governed candidate answers and performs any bounded critic-directed rerun inside `RAGTools.rag` before the terminal result is exposed.

This correction was made from source behavior, not from assumption.

## Correctness safeguards

1. **Frozen core:** the deliverable tree still matches the Phase-1 hashes for the eight protected core files.
2. **Staged integration:** Phase 4 lives in a patch; no Phase-4 core modification is silently baked into the baseline tree.
3. **Disabled by default:** all Phase-4 runtime feature flags default to false.
4. **No rejected-draft leak:** governed answer tokens are buffered until the critic accepts or abstains.
5. **Bounded retry:** environment override is clamped to at most three post-generation retries.
6. **Loop guard:** repeated focus queries terminate instead of spinning.
7. **Memory is not evidence:** planning memory is not added to chunks/references/citations.
8. **No fake similarity:** RAGFlow memory result order is used explicitly as rank, not mislabeled as raw similarity.
9. **Tenant check:** memory IDs are filtered to the dialog tenant before recall or write.
10. **Safe write:** only accepted runs may write strategy memory; original queries and generated answers are not copied into the strategy-memory envelope.
11. **Semantic write off:** memory configurations with semantic extraction are rejected by default for automatic strategy writes.
12. **No fake metrics:** no accuracy/latency/hallucination improvement is reported before live experiments.

## Offline validation result

At package build time:

- deterministic Phase-4 contract scenarios: **12 passed**;
- OmniRAG unit tests across Phase 2/3/4: **31 passed**;
- Phase-2 -> Phase-3 -> Phase-4 patch stack: **applied and syntax-compiled successfully in an isolated temp tree**;
- frozen Phase-1 core integrity: **PASS (8 protected files unchanged)**;
- Phase-4 patch scope: **2 core owner files only**.

`ruff` is not installed in the current execution environment, so a Ruff result is **not claimed**. Run `ruff check` in the later project environment after dependencies are installed.

## What is deliberately not claimed

- live model correctness;
- actual hallucination reduction;
- actual retry recovery rate;
- production latency/token cost;
- live Redis/ES/MySQL/MinIO/memory behavior;
- raw-pixel visual retrieval inside the native agentic-RAG graph.

Those require the later local/integration run.
