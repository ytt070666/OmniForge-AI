# Phase 3 — Multimodal Retrieval + Cross-modal Evidence Verification

## Why this phase exists

RAGFlow 0.27.2 already preserves image chunks (`img_id`, `doc_type_kwd`) and can
use a VISION model to describe figures during parsing. However, its normal
retrieval path still embeds/retrieves the **text representation** of a chunk.
That is useful but is not the same as a query-to-image joint embedding search.
OmniRAG therefore adds a visual sidecar retriever while keeping RAGFlow's parser,
storage, text retriever and VLM generation path intact.

## Architecture

```text
Query
  ├─> RAGFlow sparse+dense text retrieval
  └─> ModalityRouterV1
         └─(visual route)→ joint text-image query embedding
                          → visual sidecar index

Text ranked list + Visual ranked list
             ↓
Query-adaptive weighted RRF
             ↓
Agreement bonus for independently matched chunks
             ↓
Fused evidence list
             ↓
Load top retrieved image bytes from RAGFlow object storage
             ↓
Qwen3-VL / configured RAGFlow VISION generator sees text + pixels
             ↓
Claim ↔ Evidence verification
             ↓
answer + citations + omnirag_verification metadata
```

## Fusion choice

Raw RAGFlow text similarity and visual-encoder cosine similarity are not assumed
to share one calibrated scale. Phase 3 therefore uses **weighted reciprocal rank
fusion** rather than naïve raw-score addition:

`F(c|q) = wt(q)/(k+rt(c)) + wv(q)/(k+rv(c)) + agreement_bonus`

The query router controls `wt` and `wv`; explicit figure/chart/table/topology
questions receive a larger visual contribution. Exact IDs/codes remain text-first.

## Visual index

The first reproducible implementation is a JSONL cosine sidecar. This is a
research boundary, not a claim that JSONL is the final enterprise backend. The
record contract is backend-agnostic so a later Milvus or dedicated ES index can
replace it without changing fusion logic.

`phase3_build_visual_index.py --source ragflow` is already able to enumerate
RAGFlow documents/chunks, download `image_id` through the public REST API and
encode those images. No RAGFlow storage internals are required for index build.
At generation time, the guarded core patch loads the top retrieved image bytes
from RAGFlow object storage: vision-native models receive raw bytes, while
vision-capable chat models receive data-URI image blocks through the existing
RAGFlow multimodal message path.

## Evidence verifier

Phase 3 deliberately separates deterministic evidence checks from an LLM judge:

1. split answer into claims;
2. compute lexical/numeric support against retrieved evidence;
3. detect simple numeric/negation conflicts;
4. report supported-claim ratio, modality coverage and conflicts;
5. emit one decision: `pass`, `retrieve_more`, or `abstain`.

The Phase-3 core patch only **reports** this result. It does not rewrite an
answer. A later Agent/Critic phase will consume `retrieve_more` as an explicit
retry transition, which keeps Phase-3 ablations clean.

## Core isolation

The RAGFlow baseline stays untouched until experiments are collected. The
integration patch targets only `api/db/services/dialog_service.py` and is SHA-256
guarded. Phase 2's patch targets `rag/nlp/search.py`, so both innovations are
independently switchable and ablatable.

## First local-run order (later)

1. collect untouched Phase-1 text baseline;
2. apply Phase-2 patch and collect adaptive-text results;
3. install/pin visual dependencies for the actual GPU/CUDA environment;
4. build the real SigLIP2 visual sidecar;
5. check/apply Phase-3 patch;
6. run visual-only, fusion, agreement and verifier ablations;
7. only then enable a reranker and/or semantic judge.
