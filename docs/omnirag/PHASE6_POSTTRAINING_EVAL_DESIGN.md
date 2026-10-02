# OmniRAG-Agent Phase 6 — post-training, evaluation, and observability design

## 1. Scope

Phase 6 adds a **narrow, measurable post-training task** and a unified evaluation
contract. It deliberately does not fine-tune the main Qwen3-VL generation model
before the live Phase-1→5 baselines exist.

The first trainable component is an advisory control router based on
`Qwen/Qwen3-0.6B`. Its output is structured JSON describing query class,
retrieval profile, visual/tool needs, advisory tool intent, and evidence
strictness.

The router is **not** a safety boundary:

- it cannot authorize write or execute tools;
- Phase-5 ToolPolicy remains authoritative;
- Phase-3 Evidence Verifier remains authoritative;
- passing the Phase-6 promotion gate does not automatically patch RAGFlow.

This keeps learned behavior behind deterministic safety controls.

## 2. Why QLoRA first

The default experiment is QLoRA rather than full fine-tuning. The configuration
uses NF4 4-bit base weights plus a LoRA adapter with `target_modules=all-linear`.
A separate LoRA config is retained for ablation.

This is a research/engineering tradeoff: the small router is cheap enough to
iterate on, but still demonstrates a real post-training pipeline with data
lineage, adapter training, held-out evaluation, and reproducibility metadata.

## 3. Training data contract

The dataset has four partitions:

- train: 168 deterministic template examples;
- validation: 48 examples;
- synthetic test: 48 examples;
- protected benchmark: 56 existing Phase-1/3/5 questions.

Train/validation/test are split by `family_id`, not by row. Existing benchmark
questions are never used for training or validation. The builder enforces:

- no family overlap;
- no exact prompt overlap;
- no exact protected/train overlap;
- bounded 5-gram overlap with protected questions;
- secret-like data scan;
- per-file SHA-256 manifest.

Synthetic data is useful for plumbing and controlled ablation but is not a
production benchmark. The protected benchmark is stronger, yet still belongs
to this project and must not be marketed as an external benchmark.

## 4. Output schema

The model emits exactly:

```json
{
  "query_class": "semantic",
  "retrieval_profile": "dense_heavy",
  "needs_visual": false,
  "needs_tools": false,
  "tool_intent": "none",
  "evidence_strictness": "normal"
}
```

Additional fields are rejected. In particular, no `authorize`, `allow_write`,
or executable field exists in the schema.

## 5. Evaluation hierarchy

Phase 6 compares four systems:

1. deterministic rule router;
2. Qwen3-0.6B zero-shot;
3. Qwen3-0.6B + LoRA;
4. Qwen3-0.6B + QLoRA.

Each is evaluated on the synthetic test and protected benchmark. Metrics are:

- JSON/schema-valid rate;
- exact structured match;
- query-class accuracy;
- retrieval-profile accuracy;
- visual-routing F1;
- tool-routing F1;
- tool-intent accuracy on the tool subset.

End-to-end retrieval or Agent success is **not inferred** from router metrics.
Those must still be measured by the Phase-1→5 live benchmarks.

## 6. Promotion gate

`config/omnirag/phase6/promotion_gate.json` is fail-closed. Missing learned
metrics means `NOT_RUN`, not PASS. A learned adapter must at least match the
protected deterministic baseline on the configured routing metrics while also
meeting JSON-validity requirements.

Even a passing model remains advisory until a later explicit integration step.

## 7. Observability

RAGFlow already owns native Langfuse integration. OmniRAG does not instantiate a
parallel tracing backend. Phase 6 defines extension-level metric events that can
be attached to existing trace/session IDs later.

Default events exclude:

- raw prompt;
- raw completion;
- retrieved chunk text;
- raw tool arguments.

Recorded metrics include latency, token counts, retries, tool failures, and
abstention. Cost remains `null` unless a local explicit price table is supplied;
no provider pricing is invented.

## 8. Agentic RL boundary

GRPO/Agentic-RL is intentionally deferred. A credible RL experiment needs a
live tool environment, deterministic task checker, bounded action space, reward
anti-hacking tests, and SFT/reference baselines. Implementing GRPO before those
exist would create a demo rather than trustworthy evidence.

After the live Phase-5 tool benchmark is established, a later Phase 6B may add a
small tool-use GRPO experiment while keeping hard ToolPolicy outside the learned
policy.
