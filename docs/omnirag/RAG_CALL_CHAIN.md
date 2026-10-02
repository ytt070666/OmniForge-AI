# RAGFlow 0.27.2 RAG Call Chain (OmniRAG Baseline)

## A. Chat request

```text
React chat UI
  web/src/pages/next-chats/hooks/use-send-single-message.ts
        |
        v
POST /api/v1/chat/completions  (SSE)
  web/src/utils/api.ts
        |
        v
api/apps/restful_apis/chat_api.py
  session_completion()
        |
        v
api/db/services/dialog_service.py
  rag_agent()
        |
        +-- reasoning == 0 ------------------------------+
        |                                                |
        |                                                v
        |                                      async_chat()
        |                                                |
        |                                      get_models()
        |                                                |
        |                                       settings.retriever
        |                                                |
        |                                                v
        |                                     Dealer.retrieval()
        |                                      rag/nlp/search.py
        |                                                |
        |                          +---------------------+------------------+
        |                          |                     |                  |
        |                          v                     v                  v
        |                    Full-text leg          Dense/KNN leg      Rank feature
        |                          |                     |                  |
        |                          +---------- fusion/rerank --------------+
        |                                                |
        |                                                v
        |                                         top chunks
        |                                                |
        |                                                v
        |                                           kb_prompt()
        |                                                |
        |                                                v
        |                                      system prompt + history
        |                                                |
        |                                                v
        |                                         LLMBundle.chat
        |                                                |
        |                                                v
        |                                      citation/reference repair
        |                                                |
        |                                                v
        |                                              SSE
        |
        +-- reasoning > 0 --> RAGTools / agentic RAG tool path
```

## B. Document ingestion

```text
Upload document
  POST /api/v1/datasets/{dataset_id}/documents
        |
        v
api/apps/restful_apis/document_api.py
  upload_document()
        |
        v
FileService / DocumentService
        |
        v
POST /api/v1/datasets/{dataset_id}/documents/parse
        |
        v
parse_documents()
        |
        v
DocumentService.run()
        |
        v
queue_tasks() / Redis queue
        |
        v
rag/svr/task_executor.py
        |
        +--> build_chunks()
        +--> embedding()
        +--> insert_chunks()
        |
        v
Document Engine
  Elasticsearch (Phase-1 default)
        |
        v
Dealer.retrieval()
```

## C. Planned innovation hook points (do not modify in Phase 1)

1. **Adaptive Hybrid Retrieval**
   - owning path: `rag/nlp/search.py::Dealer.retrieval`
   - input to preserve: `vector_similarity_weight`
   - planned extension: query-aware routing and dynamic weighting before fusion.

2. **Multimodal retrieval**
   - owning paths: ingestion parser output + retrieval layer + `dialog_service.py` attachment handling.
   - planned extension: separate visual representation/retriever and query modality router.

3. **Evidence verification**
   - owning path: after retrieved `kbinfos`, before final response/citation decoration in `dialog_service.py`.
   - planned extension: claim-evidence scoring, conflict detection, re-retrieval.

4. **Memory-aware planning**
   - owning paths: `agent/canvas.py`, `memory/services/`, agent components.
   - planned extension: semantic/episodic/procedural memory retrieval into planning.

The rule for later phases is: extend the owner of the behavior, keep upstream changes small, and preserve a switchable baseline path for experiments.
