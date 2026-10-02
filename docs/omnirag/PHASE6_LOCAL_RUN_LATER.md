# Phase 6 local run later

Do not run these commands until the Phase-1→5 baseline environment is archived.
Training uses a **separate virtual environment** from the RAGFlow service.

## 1. Create training environment

Use Python 3.13 to match the project. Install the platform-appropriate PyTorch
build first, then:

```bash
pip install -r config/omnirag/phase6/requirements-training.txt
```

The current Phase-6 dependency contract targets Transformers 5.x, PEFT 0.21.x,
TRL 1.13.x, Datasets 5.x and bitsandbytes 0.50.x. Resolve and archive the exact
platform lock only on the actual GPU machine.

## 2. Rebuild and verify data

```bash
python3 scripts/omnirag/phase6_build_router_dataset.py
python3 scripts/omnirag/phase6_train_router.py --preflight-only
```

Do not proceed if split leakage, data hashes, or safety boundaries fail.

## 3. Base-model inference

Run both synthetic test and protected benchmark before training:

```bash
python3 scripts/omnirag/phase6_infer_router.py \
  --dataset benchmarks/omnirag/phase6/router/test.jsonl \
  --model Qwen/Qwen3-0.6B \
  --output artifacts/omnirag/phase6/base_test_predictions.jsonl

python3 scripts/omnirag/phase6_infer_router.py \
  --dataset benchmarks/omnirag/phase6/router/protected_benchmark.jsonl \
  --model Qwen/Qwen3-0.6B \
  --output artifacts/omnirag/phase6/base_protected_predictions.jsonl
```

Evaluate each output with `phase6_evaluate_router.py`.

## 4. QLoRA training

```bash
python3 scripts/omnirag/phase6_train_router.py \
  --config config/omnirag/phase6/router_sft.json
```

The default config uses Qwen3-0.6B, 4-bit NF4 QLoRA, BF16 compute, LoRA
`r=16`, `alpha=32`, and `target_modules=all-linear`.

If the GPU does not support BF16, change the config explicitly; the training
script fails instead of silently changing precision.

## 5. Adapter inference and evaluation

```bash
python3 scripts/omnirag/phase6_infer_router.py \
  --dataset benchmarks/omnirag/phase6/router/protected_benchmark.jsonl \
  --model Qwen/Qwen3-0.6B \
  --adapter artifacts/omnirag/phase6/router_adapter \
  --output artifacts/omnirag/phase6/learned_router_protected_predictions.jsonl

python3 scripts/omnirag/phase6_evaluate_router.py \
  --dataset benchmarks/omnirag/phase6/router/protected_benchmark.jsonl \
  --predictions artifacts/omnirag/phase6/learned_router_protected_predictions.jsonl \
  --output artifacts/omnirag/phase6/learned_router_protected_metrics.json

python3 scripts/omnirag/phase6_promotion_gate.py
```

A gate PASS only means the model qualifies for later integration testing.

## 6. LoRA ablation

Repeat training with:

```bash
python3 scripts/omnirag/phase6_train_router.py \
  --config config/omnirag/phase6/router_lora.json
```

Compare LoRA, QLoRA, base model, and deterministic rule baseline under the same
fixed datasets and deterministic inference settings.

## 7. Observability

When live RAGFlow execution begins, emit extension-level trace events to a JSONL
or bridge them into the existing RAGFlow/Langfuse trace. Then aggregate:

```bash
python3 scripts/omnirag/phase6_aggregate_observability.py \
  --events <live-events.jsonl> \
  --output artifacts/omnirag/phase6/observability_summary.json
```

Do not supply a price table unless it is explicitly versioned for the exact
provider/model/date used in the experiment.
