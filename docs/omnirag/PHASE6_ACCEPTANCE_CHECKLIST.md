# Phase 6 acceptance checklist

## Pre-local package

- [x] No RAGFlow core file modified by Phase 6.
- [x] Dataset generator deterministic and source-labelled.
- [x] Family-level train/validation/test isolation.
- [x] Protected Phase-1/3/5 benchmark excluded from training.
- [x] Secret-like data scan enabled.
- [x] Closed structured output schema.
- [x] Router cannot authorize write/execute tools.
- [x] QLoRA and LoRA configs prepared.
- [x] Training preflight works without model download.
- [x] Deterministic rule baseline archived.
- [x] Promotion gate is fail-closed.
- [x] Observability schema omits raw prompt/completion/tool arguments.
- [x] Cost metric remains absent without explicit price table.
- [x] Full OmniRAG offline unit suite passes.

## Deferred until local GPU/runtime

- [ ] Resolve and archive exact GPU training dependency lock.
- [ ] Base Qwen3-0.6B inference on test + protected sets.
- [ ] QLoRA training completed.
- [ ] LoRA ablation completed.
- [ ] Learned adapter inference completed.
- [ ] Promotion gate PASS or explicit non-promotion recorded.
- [ ] Phase-1→5 live system metrics archived.
- [ ] Langfuse/extension trace correlation verified.
- [ ] p50/p95 latency and token overhead measured.
- [ ] Real held-out task set collected independently of templates.
- [ ] Only after the above: consider Phase 6B Agentic-RL.
