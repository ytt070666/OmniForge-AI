# OmniOps Copilot

The user-facing application layer for OmniRAG-Agent, now served through the
OmniAI FastAPI gateway.

- Platform entry: `OMNIAI.md`
- Product guide: `docs/omnirag/OMNIOPS_PRODUCT.md`
- Install gateway deps: `pip install -r services/omniai_gateway/requirements.txt`
- Start: `python scripts/omnirag/run_omniops.py`
- Windows: `scripts\omnirag\run_omniops_windows.bat`
- UI: `http://127.0.0.1:8090`
- OpenAPI: `http://127.0.0.1:8090/docs`

Default mode is a transparent deterministic demo using local SQLite evidence.
Set `OMNIOPS_MODE=ragflow` only after a verified RAGFlow Gate-1 runtime exists.
Long-running incident analysis now uses a versioned asynchronous REST contract
(`/api/v1/analyses`) rather than holding an HTTP request open indefinitely.
