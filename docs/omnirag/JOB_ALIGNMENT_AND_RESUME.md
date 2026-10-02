# Job Alignment and Resume Pack

## Capability mapping
| Recruiting capability | OmniRAG evidence |
|---|---|
| RAG / hybrid retrieval | Phase 1 baseline + Phase 2 adaptive two-stage retrieval |
| Multimodal VLM | Phase 3 visual sidecar, modality router, pixel evidence path |
| Agent / planning / reflection | Native RAGFlow Agentic RAG + Phase 4 bounded governance |
| Memory | Phase 4 episodic/procedural planning-memory governance |
| MCP / Client-Server | RAGFlow MCP ownership + Phase 5 governed MCP tool usage |
| Tool Calling | registry, selector, schema validation, risk/budget guards |
| DSL / workflow | restricted TaskSpec compiled to RAGFlow Canvas-shaped DSL |
| Fine-tuning | Phase 6 Qwen3-0.6B LoRA/QLoRA advisory router |
| Evaluation | protected benchmarks, ablations, promotion gate, dashboard |
| Python | OmniRAG extension/training/evaluation/runtime tooling |
| React/full-stack | inherited RAGFlow UI with project integration boundary |
| Docker/Kubernetes/CI | Phase 7 deployment assets and CI; live deployment is `not_run` pre-local |

## Resume description — truthful pre-local version
**OmniRAG-Agent — RAGFlow-based enterprise multimodal Agent platform (individual project)**  
- Performed source-level secondary development on RAGFlow v0.27.2 and designed an ordered, hash-guarded extension architecture covering adaptive retrieval, multimodal evidence verification, Agent reflection/memory governance, MCP tool governance, safe workflow authoring, post-training and evaluation.
- Implemented query-adaptive two-stage hybrid retrieval and a multimodal sidecar path with text/visual rank fusion and evidence-verification interfaces; built deterministic benchmark and ablation tooling while preserving an untouched baseline.
- Built fail-closed Agent/tool governance: bounded retrieve-more reflection, tenant-aware memory rules, MCP/built-in tool registry and selection, risk/schema/budget validation, and restricted TaskSpec-to-Canvas compilation.
- Built a Qwen3-0.6B LoRA/QLoRA advisory-router pipeline with leakage checks, protected evaluation sets and a fail-closed promotion gate; learned outputs never bypass deterministic security policy.
- Added CI, hash-verified Docker build assets, Kubernetes application manifests, observability/evaluation aggregation and a dashboard that marks unexecuted live experiments as `not_run`.

## What must NOT be written before local execution
Do not claim concrete end-to-end accuracy improvement, Agent success rate, production deployment, GPU throughput, latency reduction, cost reduction or Kubernetes availability until corresponding live artifacts have been generated and reviewed.

## After local validation
Replace qualitative statements only with numbers emitted by committed evaluation artifacts. Keep the baseline, ablation configuration, dataset split, hardware and model version next to every quantitative claim.
