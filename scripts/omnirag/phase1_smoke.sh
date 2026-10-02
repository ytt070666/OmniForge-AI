#!/usr/bin/env bash
set -euo pipefail

base_url=${RAGFLOW_BASE_URL:-http://127.0.0.1:9380}

echo "Checking RAGFlow API at $base_url"

ping=$(curl -fsS "$base_url/api/v1/system/ping")
if [ "$ping" != "pong" ]; then
  echo "Unexpected ping response: $ping" >&2
  exit 1
fi
echo '[PASS] /api/v1/system/ping'

version=$(curl -fsS "$base_url/api/v1/system/version")
echo "[PASS] /api/v1/system/version -> $version"

echo 'Basic API smoke test: PASS'
