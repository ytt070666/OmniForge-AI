# OmniOps Copilot — Application Layer

OmniOps Copilot is the user-facing application built on top of OmniRAG-Agent and RAGFlow. It turns the research stack into a usable incident-analysis product without changing the frozen RAGFlow baseline or the Phase-2→5 patch contracts.

## Product scope

The first release is deliberately **read-only and analysis-first**. It supports:

- operational/security incident management;
- grounded AI chat;
- multimodal evidence browsing;
- Agent execution traces;
- MCP/tool policy visibility and audit;
- knowledge-asset staging;
- an evaluation page that preserves `not_run` for live metrics that have not been executed.

It does **not** automatically restart services, delete records, block IPs, modify production systems, or claim that locally staged files have been ingested into RAGFlow.

## Three-layer architecture

```text
RAGFlow v0.27.2
  ingestion / storage / text RAG / native Agent / MCP transport
                  ↓
OmniRAG-Agent
  adaptive retrieval / visual retrieval / evidence verification /
  reflection / memory & tool governance / post-training evaluation
                  ↓
OmniOps Copilot
  dashboard / incidents / chat / evidence / traces / tools / evaluation
```

## Run immediately in standalone demo mode

No RAGFlow runtime is required for this mode. It uses deterministic local evidence and SQLite so the product UI can be reviewed before Gate-1 runtime work is complete. The V2 HTTP edge is FastAPI, so install the gateway environment first.

```bash
pip install -r services/omniai_gateway/requirements.txt
python scripts/omnirag/run_omniops.py
```

Windows:

```bat
scripts\omnirag\run_omniops_windows.bat
```

Open `http://127.0.0.1:8090`.

Demo data is stored under `artifacts/omnirag/omniops/`. The UI clearly identifies the runtime mode.

## Connect to a verified RAGFlow runtime

Only do this after Gate 1 is complete. Set local environment variables (never commit the API key):

```text
OMNIOPS_MODE=ragflow
OMNIOPS_RAGFLOW_API_ROOT=http://127.0.0.1:9380/api/v1
OMNIOPS_RAGFLOW_API_KEY=<local secret>
OMNIOPS_RAGFLOW_CHAT_ID=<verified chat id>
```

Then restart OmniOps. Chat and incident analysis call the configured RAGFlow chat while local evidence, audit, incident state and traces remain in OmniOps SQLite.

## Demo scenarios

1. **GW-01 DNS anomaly** — log + topology + security dashboard + runbook evidence.
2. **API-GW-02 latency regression** — deployment timeline + latency chart.
3. **Patch compliance** — document-grounded SOP response.

Run an incident analysis to create a persisted Agent trace and read-only tool audit. The trace is intentionally honest in demo mode: it reports local deterministic evidence processing rather than pretending an external RAGFlow retrieval took place.

## Knowledge uploads

The product supports local staging for small PDF/DOCX/TXT/MD/CSV/PNG/JPG files. Staging is **not** equivalent to RAGFlow ingestion. A file shows `local_staged` until a future verified ingestion workflow indexes it.

## Security properties

- product V2 remains analysis/read-only by default;
- uploaded extension allowlist and size limit;
- no credentials in the SQLite model or browser application;
- tool page reflects fail-closed policy: read allowed, write/execute/unknown denied by default;
- real RAGFlow credentials are environment variables only;
- no live metric is fabricated from demo-mode activity.

## Validation

```bash
python -m unittest tests.omnirag.test_omniops_product -v
python -m py_compile apps/omniops/api/*.py scripts/omnirag/run_omniops.py
```

## OmniAI V2 gateway upgrade

The product UI is now served by `services/omniai_gateway`, a FastAPI/Pydantic v2
edge service. The API is versioned under `/api/v1`, OpenAPI is available at
`/docs`, and incident analysis is submitted as a bounded asynchronous job with
an optional `Idempotency-Key` and SSE status stream.

This migration changes the HTTP edge only. The existing OmniOps domain service,
OmniRAG evidence/governance logic, protected benchmarks and RAGFlow core
ownership remain unchanged.
