from __future__ import annotations

from .contracts import ModuleDescriptor


def default_modules() -> list[ModuleDescriptor]:
    return [
        ModuleDescriptor(id="ragflow", name="RAGFlow", role="enterprise RAG runtime", runtime="Python/Go", status="external", upstream="https://github.com/infiniflow/ragflow", license="Apache-2.0"),
        ModuleDescriptor(id="omnirag", name="OmniRAG-Agent", role="adaptive/multimodal retrieval and governance", runtime="Python", status="available"),
        ModuleDescriptor(id="fastapi", name="FastAPI Gateway", role="REST/OpenAPI gateway", runtime="Python", status="available", upstream="https://github.com/fastapi/fastapi", license="MIT"),
        ModuleDescriptor(id="langgraph", name="LangGraph Agent", role="stateful agent orchestration", runtime="Python", status="optional", upstream="https://github.com/langchain-ai/langgraph", license="MIT"),
        ModuleDescriptor(id="langchain", name="LangChain Lab", role="runnables/tools/model abstraction", runtime="Python", status="optional", upstream="https://github.com/langchain-ai/langchain", license="MIT"),
        ModuleDescriptor(id="llamaindex", name="LlamaIndex Service", role="alternative indexing/query engine", runtime="Python", status="optional", upstream="https://github.com/run-llama/llama_index", license="MIT"),
        ModuleDescriptor(id="milvus", name="Milvus Lab", role="ANN/vector database", runtime="C++/Go/Python", status="optional", upstream="https://github.com/milvus-io/milvus", license="Apache-2.0"),
        ModuleDescriptor(id="nats", name="NATS Event Bus", role="distributed messaging", runtime="Go", status="external", upstream="https://github.com/nats-io/nats-server", license="Apache-2.0"),
        ModuleDescriptor(id="otel", name="OpenTelemetry", role="distributed tracing", runtime="multi-language", status="optional", upstream="https://github.com/open-telemetry/opentelemetry-python", license="Apache-2.0"),
        ModuleDescriptor(id="tensorflow", name="TensorFlow Service", role="incident severity ML lab", runtime="Python/C++", status="optional", upstream="https://github.com/tensorflow/tensorflow", license="Apache-2.0"),
        ModuleDescriptor(id="go_realtime", name="Go Realtime Gateway", role="SSE/event fanout", runtime="Go", status="optional", upstream="https://github.com/go-chi/chi", license="MIT"),
        ModuleDescriptor(id="nestjs_bff", name="NestJS BFF", role="TypeScript aggregation learning service", runtime="Node.js/TypeScript", status="optional", upstream="https://github.com/nestjs/nest", license="MIT"),
        ModuleDescriptor(id="spring_connector", name="Spring Connector", role="enterprise connector learning service", runtime="Java", status="optional", upstream="https://github.com/spring-projects/spring-boot", license="Apache-2.0"),
    ]
