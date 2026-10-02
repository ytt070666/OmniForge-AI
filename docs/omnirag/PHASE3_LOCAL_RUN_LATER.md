# Phase 3 — Local Run Later

Do not execute this sequence until the untouched Phase-1 baseline has been collected.

## 0. Keep baseline first

```bash
bash scripts/omnirag/phase1_acceptance.sh
```

Archive `benchmarks/omnirag/phase1/results/` before applying any patch.

## 1. Phase 2 adaptive text retrieval

```bash
python3 scripts/omnirag/phase2_apply_patch.py --check
python3 scripts/omnirag/phase2_apply_patch.py --apply
```

Collect Phase-2 ablations before enabling Phase 3.

## 2. Install the real visual encoder environment

Use `config/omnirag/phase3_visual_requirements.in` as the dependency intent.
Pin exact Torch / Transformers / CUDA versions for the actual machine instead of
blindly modifying RAGFlow's primary dependency lock.

Expected environment flags:

```bash
export OMNIRAG_VISUAL_ENCODER=siglip2
export OMNIRAG_VISUAL_MODEL=google/siglip2-base-patch16-384
export OMNIRAG_VISUAL_INDEX=artifacts/omnirag/visual_index.jsonl
```

## 3. First validate the synthetic visual benchmark

```bash
python3 scripts/omnirag/phase3_build_visual_index.py \
  --source benchmark \
  --encoder siglip2

python3 scripts/omnirag/phase3_collect_multimodal.py --encoder siglip2
python3 scripts/omnirag/phase3_evaluate_multimodal.py
```

## 4. Build a visual sidecar from a real RAGFlow dataset

```bash
export RAGFLOW_API_ROOT=http://127.0.0.1:9380/api/v1
export RAGFLOW_API_KEY='...'

python3 scripts/omnirag/phase3_build_visual_index.py \
  --source ragflow \
  --dataset-id '<DATASET_ID>' \
  --encoder siglip2
```

The builder enumerates document chunks via REST, downloads chunk images via
`/documents/images/<image_id>`, and writes a joint visual index.

## 5. Activate Phase-3 integration

```bash
python3 scripts/omnirag/phase3_apply_patch.py --check
python3 scripts/omnirag/phase3_apply_patch.py --apply

export OMNIRAG_MULTIMODAL_RETRIEVAL=1
export OMNIRAG_VISUAL_ALWAYS_ON=0
export OMNIRAG_MAX_RETRIEVED_IMAGES=4
export OMNIRAG_EVIDENCE_VERIFIER=0
```

Restart the backend after patch application.

## 6. Ablation order

```bash
python3 scripts/omnirag/phase3_ablation_plan.py
```

Run fusion experiments before turning on the verifier. Then:

```bash
export OMNIRAG_EVIDENCE_VERIFIER=1
```

Phase 3 only reports `omnirag_verification`; it does not rewrite the answer.
A later Critic/Agent phase will consume `retrieve_more` and `abstain` decisions.

## Non-negotiable research rules

- Never publish hash-encoder results as model metrics.
- Keep Phase-1, Phase-2, Phase-3 result directories separate.
- Record model revision, GPU, CUDA, Torch and Transformers versions.
- Do not add reranker and verifier in the same first multimodal comparison.
- Do not overwrite the original RAGFlow baseline archive.
