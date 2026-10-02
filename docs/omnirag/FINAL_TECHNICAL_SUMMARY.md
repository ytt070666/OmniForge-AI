# OmniRAG-Agent Technical Summary

## 1. Research chain

### Phase 1 — Frozen baseline
RAGFlow v0.27.2 is preserved as the reference implementation. Baseline retrieval/generation artifacts must be collected before any core patch is activated.

### Phase 2 — Adaptive retrieval
Problem: a single fixed sparse/dense weighting is not guaranteed to be optimal across lexical, semantic, cross-lingual and visual-oriented queries.

Method: query features control both candidate acquisition and final fusion. The first live experiment is an ablation against fixed vector weights; any quality claim remains `not_run` until those artifacts exist.

### Phase 3 — Multimodal evidence
Adds a visual sidecar index, modality routing, weighted rank fusion and cross-modal evidence verification. Visual evidence is kept distinct from text captions so that a VLM can receive original image pixels when the live runtime is available.

### Phase 4 — Agent governance
RAGFlow already contains Agentic RAG planning/retrieval logic, so OmniRAG does not replace it. It adds evidence critique, bounded retrieve-more reflection, loop guards, answer buffering and memory governance. Memory is planning context, not factual evidence.

### Phase 5 — MCP/tools/DSL
RAGFlow retains MCP transport and Canvas execution ownership. OmniRAG adds a fail-closed tool registry, risk policy, top-k tool selection, schema/budget checks, HMAC-based audit metadata and a restricted TaskSpec authoring layer.

### Phase 6 — Post-training
Qwen3-0.6B is used as an advisory routing model with LoRA/QLoRA. It predicts routing metadata only and never authorizes write/execute actions. Protected benchmarks are excluded from training and a fail-closed promotion gate blocks integration if protected metrics regress.

### Phase 7 — Engineering
Adds hash-guarded Docker build assets, Compose overlay, Kubernetes application skeleton, CI, release-status artifacts and an evaluation dashboard that preserves `not_run` rather than inventing values.

## 2. Safety and correctness invariants
- Upstream RAGFlow capabilities are clearly separated from OmniRAG contributions.
- Tool annotations are treated as hints, never authorization.
- Default tool policy is read-only/closed-world; write/execute remain denied unless explicitly enabled.
- Memory never becomes citation evidence.
- Learned router output is advisory and constrained by a closed schema.
- Runtime metrics require an artifact produced by an executed experiment.
- Patch application is guarded by reviewed hashes and ordered dependencies.

## 3. Evaluation contract
The final evaluation matrix is intended to cover retrieval (Recall@K/MRR/NDCG), generation grounding, multimodal evidence, reflection behavior, tool selection/execution, memory behavior, router routing metrics, latency/tokens and deployment health. Only deterministic/static/synthetic results already produced may be reported now; live system metrics remain `not_run`.

## 4. Known pre-local limitations
- Docker/Kubernetes are not executed in the current environment.
- GPU-backed Qwen/SigLIP inference is not executed.
- Native runtime-only contracts requiring the full RAGFlow dependency stack remain deferred.
- The visual sidecar path and native Agentic RAG path share verification/governance components but are not yet claimed as a single fully validated raw-pixel Agent tool graph.
