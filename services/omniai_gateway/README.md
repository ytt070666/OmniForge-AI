# OmniAI FastAPI Gateway

The gateway is the production-facing REST/OpenAPI surface for OmniOps/OmniRAG.
It adds request IDs, bounded concurrency, local rate limiting, idempotent async
analysis submission, SSE status streaming, and Prometheus metrics.

Run from the repository root:

```bash
python -m services.omniai_gateway.main
```

Open `/docs` for OpenAPI and `/` for the OmniOps UI.

`LocalJobManager` is deliberately process-local for the laptop/demo profile.
Distributed mode uses the same analysis contract with NATS workers; do not call
the local manager a distributed queue.
