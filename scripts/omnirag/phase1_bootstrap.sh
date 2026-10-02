#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$repo_root"

action=${1:-help}

require_env() {
  bash scripts/omnirag/check_phase1_env.sh
}

case "$action" in
  check)
    require_env
    ;;
  prepare)
    require_env
    echo '[prepare] Installing Python dependencies...'
    uv sync --python 3.13 --all-extras
    echo '[prepare] Downloading RAGFlow dependency assets...'
    uv run python3 ragflow_deps/download_deps.py
    echo '[prepare] Done.'
    ;;
  dependencies)
    require_env
    echo '[dependencies] Starting RAGFlow dependency services...'
    docker compose -f docker/docker-compose-base.yml up -d
    docker compose -f docker/docker-compose-base.yml ps
    echo
    echo 'For source development, ensure these names resolve to 127.0.0.1 when applicable:'
    echo '  es01 infinity mysql minio redis sandbox-executor-manager'
    ;;
  backend)
    require_env
    if [ ! -d .venv ]; then
      echo 'Missing .venv. Run: bash scripts/omnirag/phase1_bootstrap.sh prepare' >&2
      exit 1
    fi
    export PYTHONPATH="$repo_root"
    echo '[backend] Starting Python RAGFlow API + task executor in foreground...'
    exec bash docker/launch_backend_service.sh
    ;;
  frontend)
    require_env
    cd web
    if [ ! -d node_modules ]; then
      echo '[frontend] Installing npm dependencies...'
      npm install
    fi
    echo '[frontend] Starting Vite dev server in foreground...'
    exec npm run dev
    ;;
  status)
    docker compose -f docker/docker-compose-base.yml ps || true
    echo
    echo 'Listening RAGFlow-related ports:'
    if command -v ss >/dev/null 2>&1; then
      ss -ltn | grep -E ':(80|443|9380|9381|9382|9200|3306|6379|9000|9001)\b' || true
    else
      echo 'ss command unavailable.'
    fi
    ;;
  stop)
    echo '[stop] Stopping Python backend/task executor if running...'
    pkill -f 'ragflow_server.py|task_executor.py' 2>/dev/null || true
    echo '[stop] Stopping dependency containers without deleting volumes...'
    docker compose -f docker/docker-compose-base.yml down || true
    ;;
  help|*)
    cat <<'HELP'
Usage:
  bash scripts/omnirag/phase1_bootstrap.sh check
  bash scripts/omnirag/phase1_bootstrap.sh prepare
  bash scripts/omnirag/phase1_bootstrap.sh dependencies
  bash scripts/omnirag/phase1_bootstrap.sh backend
  bash scripts/omnirag/phase1_bootstrap.sh frontend
  bash scripts/omnirag/phase1_bootstrap.sh status
  bash scripts/omnirag/phase1_bootstrap.sh stop

Recommended order:
  check -> prepare -> dependencies -> backend (terminal A) -> frontend (terminal B)
HELP
    ;;
esac
