# OmniAI third-party dependencies

OmniAI V2 adds no vendored third-party source trees. It references/install
packages and services listed in `config/omniai/upstreams.json`.

MIT projects include FastAPI template patterns, LangChain, LangGraph,
LlamaIndex, go-chi/chi, NestJS and Locust. Apache-2.0 projects include RAGFlow,
Milvus, NATS clients/server, Spring Boot/Spring AI, TensorFlow Serving,
OpenTelemetry and Prometheus client libraries.

When distributing built artifacts, preserve license notices required by the
actual packages included in those artifacts.
