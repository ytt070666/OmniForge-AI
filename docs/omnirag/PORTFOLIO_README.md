# OmniRAG-Agent

A research-oriented enterprise multimodal Agent platform built as a governed extension of RAGFlow v0.27.2.

## What is original in OmniRAG
- Query-adaptive two-stage hybrid retrieval.
- Visual sidecar retrieval and cross-modal fusion.
- Evidence verification with retrieve-more/abstain decisions.
- Bounded Agent reflection and memory governance.
- Fail-closed MCP/tool selection and execution policy.
- Safe TaskSpec authoring layer compiled to RAGFlow Canvas.
- Leakage-aware LoRA/QLoRA router training and fail-closed promotion gate.
- No-fabrication evaluation/status dashboard.

## What is inherited from RAGFlow
RAGFlow remains the underlying knowledge ingestion, retrieval/runtime, Agent Canvas, MCP integration, model abstraction, API, UI, and service foundation. OmniRAG does not relabel those upstream capabilities as original work.

## Reproducibility
All extension features default off. The original baseline is measured first; patches are applied in order and guarded by reviewed source hashes. Missing live experiments remain `not_run`.
