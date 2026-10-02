# OmniOps Copilot V2 delivery

## Delivered product surfaces

- Dashboard with runtime state and operational KPIs.
- Grounded AI workspace with citations and persisted conversation history.
- Incident Center with create/analyze flows.
- Evidence Viewer with logs, documents, topology and dashboard images.
- Agent Trace with persisted execution steps and bounded-governance decisions.
- MCP/Tool page showing fail-closed policy, registry and audit trail.
- Knowledge page with safe local staging uploads.
- Evaluation page that preserves `not_run` for unexecuted live metrics.

## Runtime modes

**Demo (default):** served through the FastAPI/Pydantic v2 gateway and backed by SQLite plus deterministic local evidence. Install `services/omniai_gateway/requirements.txt` in the gateway environment first. This mode is for product/API review and does not claim live RAGFlow performance.

**RAGFlow:** after Gate 1 is verified, set the three `OMNIOPS_RAGFLOW_*` variables. The product will call the configured RAGFlow chat and surface returned references when available.

## Product correctness boundary

OmniOps does not alter Phase-1 frozen RAGFlow core, protected benchmarks, Phase-2→5 research patches or Phase-6 promotion rules. Product-specific incident verification is intentionally scoped to the strongest evidence item per claim to avoid UI false conflicts from unrelated local evidence; this does not replace or modify the Phase-3 research verifier used by experiments.

## Quick validation

```bash
python -m unittest tests.omnirag.test_omniops_product -v
python scripts/omnirag/omniops_selfcheck.py
```

## Windows start

Double-click `start_omniops_windows.bat` or run:

```powershell
.\start_omniops_windows.ps1
```

Then open `http://127.0.0.1:8090`.

## V2 modular platform additions

OmniOps is now the product surface inside `OMNIAI.md`. FastAPI is the primary REST/OpenAPI gateway and uses `/api/v1`, request IDs, rate limiting, idempotent async analysis jobs, bounded concurrency, SSE status events and Prometheus metrics. LangGraph/LangChain/LlamaIndex/TensorFlow and the Go/Node/Java services are isolated learning/integration modules. They are not claimed as live until their individual environments are installed and tested.

The former `apps/omniops/api/server.py` standard-library HTTP server was removed so there is one HTTP edge implementation rather than two competing product servers.
