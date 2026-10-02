# OmniRAG-Agent Phase 1 Execution Report

Date: 2026-09-10

## What was executed

### 1. Baseline identified

- Upstream project: RAGFlow
- Version: `0.27.2`
- Uploaded GitHub ZIP archive commit: `a024bea0cd93f39e6652a42bf84dd20c55bc560b`
- ZIP contains no `.git` metadata, so the archive commit is recorded in `BASELINE_MANIFEST.json`.

### 2. Runtime path selected

For the first baseline we selected:

- `API_PROXY_SCHEME=python`
- `DOC_ENGINE=elasticsearch`
- MySQL + MinIO + Redis/Valkey + Elasticsearch dependency stack
- React/TypeScript/Vite frontend

The Go/hybrid runtime is intentionally not part of the first MVP.

### 3. Source paths inspected

The following paths were traced directly from the uploaded source:

- backend bootstrap and REST auto-registration
- frontend chat request and SSE parsing
- chat completion REST endpoint
- regular and reasoning/agentic RAG routing
- model resolution and LLMBundle wrapper
- hybrid retrieval and reranking implementation
- prompt knowledge assembly and citation path
- document upload, parsing queue and task executor
- Agent canvas runtime
- Memory REST/storage/search subsystem
- MCP server/client and management API

See `SOURCE_MAP.md` and `RAG_CALL_CHAIN.md` for the resulting map.

### 4. Static validation executed

Executed successfully:

- Python 3.13 compilation for `api`, `rag`, `agent`, `memory`, `mcp`, `common`
- shell syntax validation for launch/build scripts and OmniRAG helpers
- frontend `package.json` validation with Node
- project version assertion (`0.27.2`)

Result: **PASS**.

### 5. Full runtime bring-up attempted at environment level

The current ChatGPT execution sandbox was checked against the RAGFlow prerequisites.

Passed:

- CPU: 5 cores
- Python: 3.13.5
- uv: 0.10.0
- Node: 22.16.0
- npm: 10.9.2

Blocked:

- RAM: ~5.8 GB available host memory; RAGFlow requires a 16 GB class machine
- disk: ~30 GB free; upstream prerequisite is >= 50 GB
- Docker: not installed/reachable in this sandbox
- Docker Compose v2: unavailable
- `vm.max_map_count`: 65530, below Elasticsearch requirement 262144
- jemalloc metadata: not detected

Therefore a real MySQL/MinIO/Redis/Elasticsearch + backend + frontend boot cannot be completed inside this sandbox. This is an **environment limitation, not a source-code failure**.

## Key architectural findings relevant to our project

1. The first retrieval innovation should hook into `rag/nlp/search.py::Dealer.retrieval()` rather than replacing the retrieval stack.
2. The default hybrid weighting is already centralized around `vector_similarity_weight`, making it suitable for a future query-adaptive policy while preserving the original baseline.
3. Qwen3, Qwen3-VL, Qwen3-Embedding and Qwen3-Reranker are already represented in the model/provider configuration; Phase 1 should configure existing adapters instead of writing new ones.
4. RAGFlow already has a real Agent DSL/runtime (`agent/canvas.py`), Memory subsystem, MCP server/client and LangGraph dependency. Later work should extend these owners instead of adding redundant external orchestration frameworks into the core path.
5. For a multimodal chat with image attachments, `dialog_service.py` already has a vision-capability routing path. This is a future multimodal hook, but it is not yet a separate visual retrieval engine.

## Phase-1 remaining acceptance work on the user's development machine

When run on a machine that passes `scripts/omnirag/check_phase1_env.sh`, complete these runtime checks:

1. start base Docker services
2. install Python dependencies and RAGFlow dependency assets
3. start Python backend and task executor
4. start frontend
5. configure one LLM/VLM and one embedding model
6. upload a small deterministic dataset
7. parse and index it
8. run retrieval test
9. run `/api/v1/chat/completions`
10. save returned chunk scores, citation data and latency as the untouched baseline

No algorithmic core files should be modified before this checklist passes.

## Additional retrieval finding from the Elasticsearch path

A closer read of `rag/nlp/search.py::Dealer.search()` shows that Elasticsearch candidate acquisition uses a weighted-sum fusion expression configured as `0.001,1` when both lexical and dense expressions are present. The request-level `vector_similarity_weight` is then applied later in `Dealer.retrieval()` to the final local fusion/rerank score (and also affects `min_match`).

This means Phase 2 should not be limited to replacing a single constant. A stronger design is a two-stage adaptive retriever: (1) query-aware candidate acquisition / pool construction, then (2) query-aware final fusion and reranking. Phase 1 keeps both stages untouched and only measures the behavior of the public fixed-weight control.
