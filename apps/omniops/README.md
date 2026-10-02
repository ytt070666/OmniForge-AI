# OmniOps Copilot

User-facing application layer for OmniRAG-Agent and the OmniAI modular platform.

## Quick start

From the repository root, create a dedicated gateway environment and install:

```bash
pip install -r services/omniai_gateway/requirements.txt
python scripts/omnirag/run_omniops.py
```

Open:

- UI: `http://127.0.0.1:8090/`
- OpenAPI: `http://127.0.0.1:8090/docs`
- Health: `http://127.0.0.1:8090/api/v1/health`

The default demo uses SQLite plus deterministic evidence. It is a product/API smoke path, not evidence of live RAGFlow quality. See `docs/omnirag/OMNIOPS_PRODUCT.md` and `OMNIAI.md`.
