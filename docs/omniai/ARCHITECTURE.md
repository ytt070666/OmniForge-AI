# OmniAI Modular Platform architecture

```text
                         Browser / OmniOps UI
                                  |
                                  v
                         FastAPI API Gateway
                    request-id / rate-limit / OpenAPI
                    idempotency / async jobs / metrics
                                  |
               +------------------+-------------------+
               |                  |                   |
               v                  v                   v
        LangGraph Agent       OmniRAG/RAGFlow     Learning Services
       classify/retrieve      adaptive + visual    LlamaIndex / TF
       tool/generate/verify   verifier + MCP       LangChain labs
               |                  |                   |
               +---------+--------+-------------------+
                         |
                         v
                    NATS Event Bus
                         |
                 +-------+--------+
                 |                |
                 v                v
          Go Realtime SSE     Async Agent Worker
                 |
                 v
              Web clients

Optional polyglot learning boundaries:
NestJS BFF -> FastAPI Gateway
Spring Boot Connector -> MCP/tool adapter exercise
Milvus Lite -> vector/ANN lab
```

## Design rules

1. **One owner per concern.** RAGFlow owns ingestion/search runtime, OmniRAG owns
   research extensions/governance, LangGraph owns product orchestration, and the
   gateway owns HTTP edge concerns.
2. **Framework isolation.** LangChain/LlamaIndex/TensorFlow do not share the
   RAGFlow Python environment unless compatibility is explicitly verified.
3. **No metric fabrication.** Framework smoke tests are not retrieval/Agent
   quality results.
4. **Read-only by default.** Existing Phase-5 ToolPolicy remains the authority;
   a framework tool annotation is never authorization.
5. **Backpressure before scale.** Expensive Agent work is bounded and can move
   from the local job manager to NATS workers without changing the REST contract.
