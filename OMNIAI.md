# OmniAI Modular Platform

OmniAI is the modular learning/integration layer built around the existing
RAGFlow + OmniRAG-Agent + OmniOps Copilot stack.

## Quick start

Install the gateway requirements in a dedicated environment, then:

```bash
python scripts/omnirag/run_omniops.py
```

Open:

- UI: `http://127.0.0.1:8090/`
- OpenAPI: `http://127.0.0.1:8090/docs`
- Health: `http://127.0.0.1:8090/api/v1/health`
- Module registry: `http://127.0.0.1:8090/api/v1/platform/modules`

## Learning modules

- FastAPI: `services/omniai_gateway/`
- LangGraph: `services/omniai_agent/`
- LangChain: `labs/langchain_lab/`
- LlamaIndex: `services/omniai_llamaindex/`
- Vector/Milvus: `labs/vector_lab/`
- TensorFlow/Keras: `labs/tensorflow_lab/` + `services/omniai_tensorflow/`
- Go/chi + NATS SSE: `services/omniai_realtime_go/`
- NestJS: `services/omniai_bff_nest/`
- Spring Boot: `services/omniai_enterprise_spring/`
- Distributed composition: `infra/omniai/docker-compose.yml`
- Load testing: `benchmarks/omniai/load/`

Read `docs/omniai/LEARNING_PATH.md` and `docs/omniai/ARCHITECTURE.md` first.

## Verification status

Run `scripts/omniai/dev.ps1 validate` for the contract suite and read
`artifacts/runtime/FINAL_RUNTIME_REPORT.md` for this Windows machine's runtime
results. The deterministic product path and isolated learning services have
been exercised locally. Live RAGFlow benchmark gates retain their own status.

GitHub reuse rationale: `docs/omniai/GITHUB_REUSE_DECISIONS.md`.
