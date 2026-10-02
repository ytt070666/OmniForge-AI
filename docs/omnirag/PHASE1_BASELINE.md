# OmniRAG-Agent Phase 1 - Baseline Bring-up

## Goal

Create a reproducible, untouched RAGFlow baseline before any algorithmic modification.

The Phase-1 acceptance chain is:

`source start -> model configuration -> dataset upload -> parsing/indexing -> retrieval test -> chat answer -> citation -> SSE frontend display`

## Baseline selection

- RAGFlow: `0.27.2`
- Source snapshot commit: `a024bea0cd93f39e6652a42bf84dd20c55bc560b`
- API runtime: Python (`API_PROXY_SCHEME=python`)
- Document engine: Elasticsearch
- Metadata DB: MySQL
- Object storage: MinIO
- cache/queue: Redis/Valkey
- Frontend: React + TypeScript + Vite

Do **not** use the Go/hybrid runtime in the first baseline.

## Machine requirements

Official source/self-host prerequisites in this snapshot require at least:

- 4 CPU cores
- 16 GB RAM
- 50 GB free disk
- Docker >= 24
- Docker Compose >= 2.26.1
- Python >= 3.13 and < 3.14
- Node >= 18.20.4 for frontend source development
- `vm.max_map_count >= 262144` for Elasticsearch

Code Executor/Sandbox additionally requires gVisor; it is **not** a Phase-1 blocker.

Run:

```bash
bash scripts/omnirag/check_phase1_env.sh
```

## Recommended first bring-up

### 1. Start dependency services

```bash
cd <repo-root>
docker compose -f docker/docker-compose-base.yml up -d
```

For source development, ensure the service names resolve locally. On Linux the upstream instructions use:

```text
127.0.0.1 es01 infinity mysql minio redis sandbox-executor-manager
```

Only the hosts required by the selected profile must actually be running.

### 2. Install Python dependencies

```bash
uv sync --python 3.13 --all-extras
uv run python3 ragflow_deps/download_deps.py
```

The dependency/model download can be large. Keep at least 50 GB free before starting.

### 3. Start the Python backend

```bash
source .venv/bin/activate
export PYTHONPATH=$(pwd)
bash docker/launch_backend_service.sh
```

This starts the API server and task executor by default.

Expected API port: `9380`.

### 4. Start frontend

In another terminal:

```bash
cd web
npm install
npm run dev
```

### 5. Configure models

For Phase 1, use one chat/VLM model and one embedding model through RAGFlow's existing provider UI/API. Do not write a new provider adapter yet.

Preferred quick path:

- Chat/VLM: an already-supported Qwen/Qwen-VL compatible provider or another available API model.
- Embedding: an already-supported Qwen3-Embedding/BGE model or external embedding API.
- Reranker: optional for the very first smoke test; enable after plain retrieval is working.

If using the optional local TEI profile, note that the default `Qwen/Qwen3-Embedding-0.6B` entry in `docker/.env` is documented as requiring about 25 GB RAM/VRAM. For a small local machine, do not start with this default.

## Baseline smoke-test dataset

Use a tiny deterministic dataset first, not a large thesis corpus. Prepare 3 documents:

1. `product_a.txt`: contains one unique fact A.
2. `product_b.txt`: contains one unique fact B.
3. `policy.pdf`: contains one short table and one unique policy fact.

Minimum questions:

- direct fact query for document A
- direct fact query for document B
- negative query whose answer is absent
- table/policy query
- multi-turn follow-up query

Record retrieved chunks and answer references for each.

## Acceptance criteria

Phase 1 is complete only when all items below pass:

- [ ] Environment checker has no blocking failures.
- [ ] Dependency containers are healthy.
- [ ] Python API starts on 9380.
- [ ] Task executor stays alive.
- [ ] Frontend starts and can log in.
- [ ] A chat/VLM model is configured and responds.
- [ ] An embedding model is configured and encodes queries.
- [ ] A dataset can be created.
- [ ] A document can be uploaded.
- [ ] Parsing reaches DONE and creates chunks.
- [ ] Retrieval test returns the expected chunk.
- [ ] `/api/v1/chat/completions` streams a response.
- [ ] Final response includes reference/citation data for an in-KB question.
- [ ] An absent answer does not falsely cite unrelated content.
- [ ] Baseline retrieval settings are recorded (`top_n`, `top_k`, similarity threshold, vector similarity weight, reranker).

## Baseline metrics to save

For every test query save:

- query
- expected document/chunk
- returned chunk IDs
- term similarity
- vector similarity
- final similarity
- answer
- citations
- total latency
- retrieval latency
- generated token count

Do this **before** Adaptive Retrieval or Evidence Verifier changes. These rows become our experimental baseline.

## Current sandbox status (2026-09-10)

Static inspection in the ChatGPT execution sandbox passed for Python source compilation and shell syntax, but a full server bring-up cannot be completed in this sandbox because it has:

- about 5.8 GB RAM (below 16 GB)
- about 30 GB free disk (below 50 GB)
- no Docker binary/daemon
- local Go 1.23.2 while this snapshot requests Go 1.26.4 (Go is optional for our Python Phase-1 path)

The uploaded code itself is therefore not treated as failed; the runtime environment is the blocker.
