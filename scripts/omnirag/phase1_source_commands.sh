#!/usr/bin/env bash
set -euo pipefail

cat <<'CMDS'
# Run from the RAGFlow repository root on a machine that passes check_phase1_env.sh.

# 0) Verify machine
bash scripts/omnirag/check_phase1_env.sh

# 1) Python environment and native/model dependencies
uv sync --python 3.13 --all-extras
uv run python3 ragflow_deps/download_deps.py

# 2) Start MySQL + MinIO + Redis + Elasticsearch dependencies
# Default docker/.env uses COMPOSE_PROFILES based on DOC_ENGINE and metadata DB.
docker compose -f docker/docker-compose-base.yml up -d

# 3) Linux source-development hostname mapping (review before applying)
# 127.0.0.1 es01 infinity mysql minio redis sandbox-executor-manager

# 4) Start Python backend + task executor
source .venv/bin/activate
export PYTHONPATH=$(pwd)
bash docker/launch_backend_service.sh

# 5) In a second terminal, start frontend
cd web
npm install
npm run dev
CMDS
