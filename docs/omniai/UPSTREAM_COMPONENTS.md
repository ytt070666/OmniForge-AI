# OmniAI upstream integration review

Checked: **2026-09-29**.

The repository search found mature upstream projects that fit the learning
platform directly. OmniAI V2 therefore does **not** reimplement these frameworks
and does **not** vendor their source trees. It integrates them as isolated
packages/services and keeps original ownership clear.

| Upstream | How OmniAI uses it | Why not copy the repository |
|---|---|---|
| FastAPI Full Stack Template | API/OpenAPI/Docker/CI design reference | Its full product template would duplicate the existing RAGFlow/OmniOps UI and persistence layers. |
| LangGraph | Real state graph in `services/omniai_agent` | Package integration is the intended reuse boundary. |
| LangChain | LCEL/tool learning lab | Keeping it isolated avoids forcing its release cadence into RAGFlow. |
| LlamaIndex | Independent index/retrieval service | Useful for framework comparison without replacing OmniRAG. |
| Milvus | Optional Milvus Lite vector lab | RAGFlow already owns the production search backend; the lab teaches ANN/vector DB concepts. |
| NATS | Distributed analysis/event transport | RAGFlow already includes NATS infrastructure, so OmniAI reuses the same technology. |
| go-chi/chi | Go SSE/realtime service | Small idiomatic router; avoids inventing a custom Go framework. |
| NestJS | Optional Node/TypeScript BFF | Provides a realistic Node module/controller service without changing the FastAPI source of truth. |
| Spring Boot / Spring AI | Java connector and future Java-AI lab | Enterprise connector is a better Java learning boundary than duplicating the Python Agent. |
| TensorFlow Serving | Optional serving target | TensorFlow is kept as a distinct ML-learning path rather than mixed into the Transformers pipeline. |
| OpenTelemetry / Prometheus | Observability | Standard protocols/clients are preferred over a custom tracing/metrics backend. |
| Locust | Load tests | External load generator; no need to embed load-generation code into production services. |

## License stance

Selected dependencies are MIT or Apache-2.0. No third-party source code was
copied into OmniAI V2. Dependency licenses remain those of their upstream
projects. `config/omniai/upstreams.json` is the machine-readable inventory.

## Important compatibility decision

The base RAGFlow tree currently pins its own LangGraph version. The learning
platform therefore puts modern LangChain/LangGraph/LlamaIndex environments in
**separate service virtual environments/containers**. This is intentional
microservice isolation, not duplicate business logic.
