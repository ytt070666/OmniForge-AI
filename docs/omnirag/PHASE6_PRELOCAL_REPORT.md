# OmniRAG-Agent Phase 6 pre-local report

## Status

Phase 6 is **pre-local code-complete** for a narrow LoRA/QLoRA post-training
pipeline, leakage-controlled data preparation, structured router evaluation,
promotion gating, and privacy-reduced extension observability.

No model weights were downloaded, no GPU training was run, and no live RAGFlow
service was started in this phase.

## Design correction

The main Qwen3-VL/RAG stack is not fine-tuned yet. Fine-tuning it before live
baseline and error analysis would make attribution weak and compute expensive.
Instead Phase 6 trains a small advisory control router whose output can be
evaluated independently.

## Data

Generated deterministically from human-authored templates:

- train: 168;
- validation: 48;
- synthetic test: 48.

Protected evaluation-only questions imported from existing project benchmarks:

- Phase 1: 28;
- Phase 3: 18;
- Phase 5: 10;
- total protected: 56.

Protected questions are excluded from train/validation. Current builder reports
zero exact overlap and zero 5-gram overlap between train and the protected set.

## Offline baseline

The transparent deterministic rule router currently produces:

- synthetic test exact structured match: 0.7292;
- protected exact structured match: 0.7857;
- protected JSON/schema validity: 1.0000;
- protected visual-routing F1: 0.7742;
- protected tool-routing F1: 0.9474;
- protected tool-intent accuracy on tool subset: 0.9000.

These are **router-only engineering baselines**, not end-to-end RAG/Agent
results. They are archived so a learned router has something reproducible to
beat.

## Post-training contract

Default: `Qwen/Qwen3-0.6B` + QLoRA/NF4 + LoRA on all linear layers.

Training dependencies are isolated from RAGFlow runtime dependencies. Exact
platform-specific PyTorch/GPU lock is intentionally deferred until the real
machine is known; no fake lockfile is produced.

## Observability

RAGFlow retains ownership of native Langfuse tracing. OmniRAG adds a structured
extension event contract only. Raw prompts, completions, retrieved chunk text,
and tool arguments are not fields in the default event schema.

No model price is hard-coded. Cost remains null unless an explicit local price
table is supplied.

## Boundaries

Not claimed as complete yet:

- actual LoRA/QLoRA training;
- adapter quality improvement;
- end-to-end task success improvement;
- latency/token savings;
- production cost reduction;
- VLM fine-tuning;
- Agentic RL/GRPO;
- real held-out production benchmark.

These require the later local/live run.
