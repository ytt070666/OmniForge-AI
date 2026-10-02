# OmniAI learning path

The goal is to learn each technology in isolation, then understand why it is
used in the composed system.

1. **LLM + Transformers** — revisit Phase 6 router, tokenizer/generation/LoRA.
2. **Vector fundamentals** — `labs/vector_lab/cosine_search.py`, then Milvus Lite.
3. **RAG** — Phase 1/2/3 baselines, hybrid/adaptive/visual retrieval.
4. **LangChain** — runnables, parallel composition and tool schemas.
5. **LangGraph** — state, nodes, conditional edges, bounded reflection.
6. **LlamaIndex** — Document/Index/Retriever and compare its retrieval contract.
7. **FastAPI** — Pydantic v2, OpenAPI, middleware, async jobs and SSE.
8. **Distributed systems** — NATS queue groups, idempotency, backpressure,
   timeout/retry/circuit-breaker and stateless gateway scaling.
9. **Go** — chi middleware, goroutines and SSE fan-out.
10. **Node/NestJS** — modules/controllers/BFF aggregation.
11. **Java/Spring Boot** — enterprise connector and actuator; optionally extend
    with Spring AI after the connector contract is understood.
12. **TensorFlow** — Keras model lifecycle and serving as a separate ML service.
13. **Observability** — Prometheus/OpenTelemetry/Langfuse responsibilities.
14. **Deployment** — Docker profiles, then Kubernetes only after single-host
    runtime verification.

Every lab has a clear claim boundary. Completing a lab means you can explain
its mechanics; it does not automatically prove production performance.
