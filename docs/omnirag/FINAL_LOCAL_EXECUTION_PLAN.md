# Final Local Execution Plan

This plan converts the current `pre-local ready` repository into a runtime-verified portfolio. Do not skip gates.

## Gate 0 — Environment
1. Run Phase-1 environment checks.
2. Install the full RAGFlow dependency stack.
3. Verify Docker/Compose, disk/RAM, `vm.max_map_count`, GPU/driver if local models are used.
4. Run the static master acceptance before starting services.

## Gate 1 — Untouched RAGFlow baseline
- Start official baseline with all OmniRAG feature flags off.
- Configure the chosen embedding/chat models.
- Ingest the fixed Phase-1 corpus.
- Collect fixed-weight retrieval runs and generation artifacts.
- Freeze the baseline result directory and hash it.

## Gate 2 — Phase 2 ablation
Apply only Phase 2. Compare fixed-weight baselines with adaptive-final, adaptive-candidate and adaptive-two-stage settings. No other extension may be enabled during this gate.

## Gate 3 — Phase 3 multimodal
Apply Phase 3, build the visual sidecar index and execute the 18 protected multimodal queries. Verify that visual hits map to original RAGFlow images and that evidence-verifier decisions are persisted.

## Gate 4 — Phase 4 Agent governance
Enable governance on native Agentic RAG. Test accept/retrieve-more/abstain, retry budget, duplicate-query loop guard, answer buffering and memory tenant/type rules.

## Gate 5 — Phase 5 MCP/tool runtime
Start the reference MCP server and RAGFlow MCP client path. Execute read-only tools, then negative tests for write/execute/open-world defaults. Inspect both OmniRAG audit and native RAGFlow logs for sensitive argument leakage.

## Gate 6 — Phase 6 training
Train the Qwen3-0.6B router with LoRA and QLoRA separately. Evaluate zero-shot, rule baseline, LoRA and QLoRA on the same synthetic test and protected benchmark. Run the promotion gate; do not integrate a failing adapter.

## Gate 7 — Product/deployment
Build the hash-guarded image, start Compose overlay, run health/smoke tests, generate observability/evaluation artifacts, then test the Kubernetes application skeleton on a disposable namespace.

## Gate 8 — Final evidence freeze
Generate `final_release_status.json`, dashboard and experiment table. Every resume number must point to a committed result artifact. Anything not executed remains `not_run`.
