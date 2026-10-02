# GitHub reuse and composition decisions

Checked: **2026-09-29**.

OmniAI intentionally reuses mature upstream projects through package/service boundaries instead of copying whole source trees into RAGFlow. This keeps upstream ownership, licenses and upgrade paths explicit while preserving the existing OmniRAG research core.

| Project | Repository | OmniAI decision |
|---|---|---|
| FastAPI Full Stack Template | https://github.com/fastapi/full-stack-fastapi-template | Design reference for API/OpenAPI/Docker/CI; do not copy its full app because OmniOps already owns UI/domain data. |
| LangGraph | https://github.com/langchain-ai/langgraph | Isolated dependency in `services/omniai_agent`; owns product orchestration/state graph. |
| LangChain | https://github.com/langchain-ai/langchain | Isolated LCEL/tool lab; not installed into RAGFlow's base environment. |
| LlamaIndex | https://github.com/run-llama/llama_index | Independent retrieval/index service for learning and framework comparison. |
| Milvus | https://github.com/milvus-io/milvus | Milvus Lite lab for ANN/vector-database learning; it does not silently replace RAGFlow search. |
| NATS Python/Go | https://github.com/nats-io/nats.py / https://github.com/nats-io/nats.go | Optional distributed job/event transport and Go realtime bridge. |
| go-chi/chi | https://github.com/go-chi/chi | HTTP/router dependency for the Go SSE service. |
| NestJS | https://github.com/nestjs/nest | Optional TypeScript BFF learning service. |
| Spring Boot / Spring AI | https://github.com/spring-projects/spring-boot / https://github.com/spring-projects/spring-ai | Read-only enterprise connector now; Spring AI kept as a future Java-side AI exercise rather than duplicating Python Agent logic. |
| TensorFlow Serving | https://github.com/tensorflow/serving | Serving reference for the independent TensorFlow/Keras learning module. |
| OpenTelemetry / Prometheus | https://github.com/open-telemetry/opentelemetry-python / https://github.com/prometheus/client_python | Standard observability interfaces; no custom telemetry backend invented. |
| Locust | https://github.com/locustio/locust | External load-test driver for concurrency experiments. |

## Compatibility rule

RAGFlow's current `pyproject.toml` pins `langgraph==1.2.0`, while the contemporary LangChain package reviewed for this platform requires a newer LangGraph range. Therefore modern LangChain/LangGraph/LlamaIndex are intentionally isolated in separate environments/containers. We do not relax RAGFlow's upstream pin merely to make a learning lab importable.

## License rule

The selected integration inventory is limited to MIT or Apache-2.0 projects. Their source trees are not vendored by OmniAI V2. `config/omniai/upstreams.json` is the machine-readable inventory.
