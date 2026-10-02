# OmniAI V2 integration report

## What was reused

- FastAPI ecosystem patterns for the new edge gateway.
- LangGraph as the actual state-machine implementation for the new Agent service.
- LangChain as a focused LCEL/tool lab.
- LlamaIndex as an independent retrieval service for comparison and learning.
- Milvus Lite as an optional vector-database lab.
- NATS for the distributed-worker/event path already consistent with RAGFlow.
- chi/NestJS/Spring Boot as isolated Go/Node/Java learning services.
- TensorFlow/Keras as a separate ML service instead of contaminating the
  Transformers/PEFT LLM environment.
- Prometheus/OpenTelemetry extension points for observability.

## What was improved beyond upstream templates

- Frameworks are connected through explicit service contracts instead of being
  copied into one monolithic dependency environment.
- Existing OmniRAG safety boundaries remain authoritative across LangGraph and
  MCP tools.
- Long-running analysis uses a 202-style asynchronous job contract and SSE
  status stream; the local job manager can later be replaced by NATS workers.
- Gateway request IDs, idempotency, rate limiting, concurrency gates and
  Prometheus metrics are part of the application edge.
- The same OmniOps domain/evidence store is reused; the platform does not create
  a second incident model merely to showcase another framework.

## Runtime evidence

The Windows target machine has now run isolated LangGraph, LlamaIndex,
TensorFlow, Go, NestJS, Spring, NATS and Compose checks. Exact PASS/FAIL/DEFERRED
status and commands are recorded in `artifacts/runtime/FINAL_RUNTIME_REPORT.md`.
RAGFlow Gate 1 and protected quality benchmarks require separate evidence.

The deterministic GW-01 integration smoke traverses the FastAPI Gateway's
optional Agent HTTP route into the real LangGraph service, checks its evidence
verification and read-only device lookup, and separately verifies the MCP HTTP
tool transport. The OmniOps async job returns citations, trace steps and SSE.
It is explicitly tagged `deterministic_product` until RAGFlow Gate 1 runs.

Qwen3-0.6B base inference and isolated LoRA/QLoRA synthetic training also ran
in a local isolated environment. Their adapters remain outside the product: the protected
comparison and fail-closed promotion gate have not passed.
