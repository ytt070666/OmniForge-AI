#!/usr/bin/env bash
set -eu

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$repo_root"

printf '%s\n' 'OmniRAG-Agent Phase-1 acceptance runner'
printf '%s\n' '======================================='

bash scripts/omnirag/phase1_static_validate.sh

if [ "${OMNIRAG_SKIP_ENV_CHECK:-0}" != "1" ]; then
  bash scripts/omnirag/check_phase1_env.sh
fi

if [ -z "${RAGFLOW_API_KEY:-}" ]; then
  printf '%s\n' '[FAIL] RAGFLOW_API_KEY is not set.' >&2
  printf '%s\n' 'Create/copy an HTTP API key in RAGFlow, then run:' >&2
  printf '%s\n' '  export RAGFLOW_API_KEY="..."' >&2
  exit 1
fi

python3 scripts/omnirag/phase1_collect_baseline.py "$@"
python3 scripts/omnirag/phase1_evaluate_baseline.py
python3 scripts/omnirag/phase1_evaluate_generation.py --allow-missing

printf '%s\n' '======================================='
printf '%s\n' 'Phase-1 baseline collection and evaluation completed.'
