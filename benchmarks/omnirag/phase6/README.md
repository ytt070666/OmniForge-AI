# OmniRAG Phase 6 benchmark

Phase 6 adds a **small, advisory post-training task** rather than fine-tuning the
main RAG/VLM stack before a live baseline exists.

## Why this task

The first trained model is a `Qwen/Qwen3-0.6B` control router. It predicts:

- query class;
- retrieval profile;
- whether visual retrieval is useful;
- whether tools are useful;
- an advisory tool intent;
- evidence strictness.

It **cannot authorize a tool**. Phase-5 deterministic tool policy remains the
security boundary. It also cannot replace Phase-3 evidence verification.

## Data split

`router/train.jsonl`, `validation.jsonl`, and `test.jsonl` are generated only
from human-authored deterministic templates. Split assignment is by
`family_id`, not by individual row, so one paraphrase family cannot appear in
multiple splits.

`router/protected_benchmark.jsonl` is made from the existing Phase-1, Phase-3,
and Phase-5 benchmark questions. It is evaluation-only and is explicitly
excluded from training and validation.

No external LLM generates training examples in this pre-local package.

## Important metric boundary

The deterministic router baseline and the synthetic test split are engineering
smoke baselines. A resume/paper claim about learned-router improvement requires
running both the base model and adapter on the protected benchmark and later on
a separately collected real held-out task set.
