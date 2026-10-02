# OmniRAG-Agent

> Enterprise multimodal Agent research platform implemented as a governed extension of **RAGFlow v0.27.2**.

**Current stage:** `pre-local ready`  
**Live runtime status:** `not_run`  
**Baseline policy:** RAGFlow core remains frozen until the original baseline is measured.

## Why this project exists
OmniRAG-Agent is designed as one flagship project covering the recurring capabilities requested by large-model application, Agent, multimodal RAG and AI full-stack roles: retrieval, multimodality, evidence verification, agentic reflection, memory, MCP/tools, workflow DSL, post-training, evaluation, observability and deployment engineering.

## Architecture
See `artifacts/omnirag/phase8/architecture.svg`.

## Original OmniRAG work
1. Query-adaptive two-stage hybrid retrieval.
2. Visual sidecar retrieval, multimodal fusion and evidence verification.
3. Bounded reflection and memory governance over native RAGFlow Agentic RAG.
4. Fail-closed tool registry/selection/governance for built-in and MCP tools.
5. Restricted TaskSpec authoring compiled to RAGFlow Canvas-shaped DSL.
6. Leakage-aware LoRA/QLoRA advisory router with a protected promotion gate.
7. No-fabrication evaluation status, observability extensions, reproducible patch stack and productization assets.

## Inherited from RAGFlow
RAGFlow remains the owner of knowledge ingestion, core retrieval/runtime, Agent Canvas, MCP transport/integration, model abstraction, API, UI and service infrastructure. These upstream capabilities are not relabeled as original OmniRAG work.

## Reproducibility
- Phase-1 core files are hash-locked.
- Extension features are opt-in and default off.
- Patches are applied in ordered phases only after reviewed source hashes match.
- Protected evaluation data is excluded from router training.
- Missing live experiments are recorded as `not_run`; the project does not fabricate runtime metrics.

## Local execution sequence
Do not enable all features at once. Follow `docs/omnirag/FINAL_LOCAL_EXECUTION_PLAN.md` and measure:

`Baseline -> Phase 2 -> Phase 3 -> Phase 4 -> Phase 5 -> Phase 6 -> Deployment/Observability`.

## Current verification boundary
Static contracts, unit tests, patch-stack compilation and artifact consistency are verified in the pre-local environment. Docker runtime, Kubernetes apply, GPU model execution and end-to-end quality metrics remain `not_run` until a suitable local/server environment is used.
