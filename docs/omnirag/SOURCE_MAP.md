# OmniRAG-Agent Phase 1 Source Map

## 1. Baseline conclusion

This code snapshot is RAGFlow `0.27.2`. The GitHub ZIP archive comment identifies the source commit as:

`a024bea0cd93f39e6652a42bf84dd20c55bc560b`

For the first development baseline, use the **pure Python API path** (`API_PROXY_SCHEME=python`). Do not introduce the Go runtime into the MVP unless a feature specifically requires it. This keeps the first iteration aligned with the target job requirements (Python / RAG / Agent / LLM application engineering) and reduces debugging surface.

## 2. Top-level ownership map

| Path | Role | Phase-1 priority | Later OmniRAG use |
|---|---|---:|---|
| `api/` | Quart API server, REST routes, DB services, model/dataset/chat services | P0 | Main integration layer |
| `rag/` | Retrieval, embedding/rerank glue, LLM adapters, RAG prompts, task executor, advanced RAG | P0 | Adaptive retrieval / multimodal retrieval / verifier |
| `deepdoc/` | OCR and document parsing | P1 | Multimodal document ingestion |
| `agent/` | Python workflow canvas, components, tools, templates, sandbox integration | P1 | Planner / critic / workflow extensions |
| `memory/` | Memory message storage/search utilities | P1 | Long-term memory strategy |
| `mcp/` | MCP client/server implementation | P1 | Custom MCP tools |
| `common/` | Global settings, doc-store abstractions, common utilities | P0 | Runtime wiring and hooks |
| `conf/` | Model/provider definitions and system config | P0 | Qwen/VLM/embedding provider setup |
| `web/` | React + TypeScript + Vite frontend | P1 | Project UI and observability pages |
| `internal/` | Large Go runtime/server/ingestion implementation | P2 | Keep unchanged in initial Python baseline |
| `docker/` | Compose files, env defaults, backend launch scripts | P0 | Local development/deployment |

## 3. Server bootstrap path

The Python backend starts from:

`api/ragflow_server.py -> run_server()`

The important sequence is:

1. `settings.init_settings()` loads DB, model, document-engine, storage and global retriever configuration.
2. DB tables and seed data are initialized.
3. plugins are loaded.
4. background progress/chat-channel services start.
5. Quart starts on the configured RAGFlow host/port.

REST modules are dynamically registered in `api/apps/__init__.py`.
Files under `api/apps/restful_apis/` receive the prefix `/api/v1`.

## 4. Core RAG request path

Frontend entry:

`web/src/pages/next-chats/hooks/use-send-single-message.ts`

The frontend sends an SSE POST to:

`web/src/utils/api.ts -> /api/v1/chat/completions`

Backend path:

`api/apps/restful_apis/chat_api.py::session_completion()`

Then:

`api/db/services/dialog_service.py::rag_agent()`

Two main modes exist:

- `reasoning == 0`: regular RAG through `async_chat()`.
- `reasoning > 0`: agentic RAG through `RAGTools`, except several fallbacks (for example vision attachments or models without tool calling).

The regular RAG path is the first modification target because it is simpler, stable, and already carries all core retrieval/citation behavior.

## 5. Regular RAG internals

`api/db/services/dialog_service.py::async_chat()` performs:

1. Resolve chat/VLM model.
2. Build `LLMBundle` instances for embedding/chat/rerank/TTS with `get_models()`.
3. Resolve document scope and metadata filters.
4. Optionally refine multi-turn questions / translate / extract keywords.
5. Call `settings.retriever.retrieval(...)`.
6. Convert retrieved chunks into prompt knowledge using `kb_prompt(...)`.
7. Attach files/images when supported.
8. Call the model through `LLMBundle.async_chat*`.
9. Generate/fix citations and return references.

The global retriever is created in:

`common/settings.py::init_settings()`

as:

`retriever = rag.nlp.search.Dealer(docStoreConn)`

## 6. Retrieval engine

Main file:

`rag/nlp/search.py`

Main class:

`Dealer`

Important methods:

- `get_vector()` - query embedding -> dense expression.
- `search()` - executes full-text/vector query against the selected document engine.
- `rerank_with_knn()` - ES KNN score + local token similarity fusion.
- `rerank()` - local hybrid similarity path for selected engines.
- `rerank_by_model()` - external/cross-encoder reranker path.
- `retrieval()` - candidate retrieval, reranking, filtering, pagination and returned chunk construction.
- `insert_citations()` - citation insertion support.

### Current hybrid score

For the default ES non-reranker path the effective local combination is conceptually:

`score = (1 - vector_similarity_weight) * term_similarity + vector_similarity_weight * vector_similarity + rank_features`

The current weight is a user/config value, normally defaulting to `0.3` for vector similarity.

**This is the cleanest hook for the future Query-Adaptive Retrieval innovation.**
Do not edit it during Phase 1; first preserve it as the benchmark baseline.

## 7. Document ingestion path

Frontend upload endpoint:

`/api/v1/datasets/{dataset_id}/documents`

Backend:

`api/apps/restful_apis/document_api.py::upload_document()`

Parsing endpoint:

`/api/v1/datasets/{dataset_id}/documents/parse`

Backend:

`document_api.py::parse_documents()`

Then:

`DocumentService.run()`

which queues either a dataflow pipeline or normal document tasks.

Python worker:

`rag/svr/task_executor.py`

Important worker steps include:

- task collection
- document chunk construction
- embedding
- chunk insertion into the document engine
- progress/status update

For Phase 1, the minimum baseline to prove is:

`Upload -> Parse -> Chunk -> Embed -> Index -> Retrieve -> Generate -> Cite`

## 8. Model layer

Primary runtime wrapper:

`api/db/services/llm_service.py::LLMBundle`

Key interfaces used by RAG:

- `encode_queries()`
- `similarity()`
- `async_chat()`
- `async_chat_streamly()`
- `async_chat_streamly_delta()`

Provider/model metadata lives mainly in:

- `conf/llm_factories.json`
- `conf/models/*.json`
- `rag/llm/`

This snapshot already contains Qwen3, Qwen3-VL, Qwen3-Embedding and Qwen3-Reranker definitions. Therefore the first baseline should use existing provider abstractions rather than adding a new Qwen adapter.

## 9. Agent / Memory / MCP status discovered in this snapshot

These are already real subsystems, not placeholders:

- Agent graph runtime: `agent/canvas.py` (`Graph`, `Canvas`).
- Memory REST API: `api/apps/restful_apis/memory_api.py`.
- Memory storage/search: `memory/services/`.
- MCP server/client: `mcp/server/server.py`, `mcp/client/`.
- MCP management API: `api/apps/restful_apis/mcp_api.py`.

This matters for our project plan: later phases should **extend** these owning abstractions instead of bolting on unrelated frameworks.

## 10. Phase-1 protected baseline

Until the baseline acceptance test passes, do not modify these files:

- `rag/nlp/search.py`
- `api/db/services/dialog_service.py`
- `agent/canvas.py`
- `memory/services/*`
- `mcp/server/server.py`

First record metrics and behavior. Innovation starts only after the baseline is reproducible.
