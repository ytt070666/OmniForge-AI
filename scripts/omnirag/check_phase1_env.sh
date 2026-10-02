#!/usr/bin/env bash
set -u

fail=0
warn=0

pass() { printf '[PASS] %s\n' "$1"; }
warn_msg() { printf '[WARN] %s\n' "$1"; warn=$((warn + 1)); }
fail_msg() { printf '[FAIL] %s\n' "$1"; fail=$((fail + 1)); }

version_ge() {
  [ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -n1)" = "$2" ]
}

printf 'OmniRAG-Agent Phase-1 environment check\n'
printf '%s\n' '--------------------------------------'

cores=$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 0)
if [ "$cores" -ge 4 ] 2>/dev/null; then pass "CPU cores: $cores"; else fail_msg "CPU cores: $cores (need >= 4)"; fi

if command -v free >/dev/null 2>&1; then
  mem_kb=$(awk '/MemTotal/ {print $2}' /proc/meminfo 2>/dev/null || echo 0)
  mem_gb=$((mem_kb / 1024 / 1024))
  if [ "$mem_gb" -ge 15 ]; then pass "RAM: about ${mem_gb} GiB"; else fail_msg "RAM: about ${mem_gb} GiB (need >= 16 GB class)"; fi
else
  warn_msg 'Cannot determine RAM automatically on this OS.'
fi

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
avail_kb=$(df -Pk "$repo_root" | awk 'NR==2 {print $4}')
avail_gb=$((avail_kb / 1024 / 1024))
if [ "$avail_gb" -ge 50 ]; then pass "Free disk: about ${avail_gb} GiB"; else fail_msg "Free disk: about ${avail_gb} GiB (need >= 50 GB)"; fi

if command -v docker >/dev/null 2>&1; then
  docker_version=$(docker version --format '{{.Client.Version}}' 2>/dev/null || docker --version | sed -E 's/.*version ([0-9.]+).*/\1/')
  if version_ge "$docker_version" '24.0.0'; then pass "Docker: $docker_version"; else fail_msg "Docker: $docker_version (need >= 24.0.0)"; fi
  if docker info >/dev/null 2>&1; then pass 'Docker daemon is reachable.'; else fail_msg 'Docker client exists but daemon is not reachable.'; fi
else
  fail_msg 'Docker is not installed or not on PATH.'
fi

if docker compose version >/dev/null 2>&1; then
  compose_version=$(docker compose version --short 2>/dev/null | sed 's/^v//')
  if version_ge "$compose_version" '2.26.1'; then pass "Docker Compose: $compose_version"; else fail_msg "Docker Compose: $compose_version (need >= 2.26.1)"; fi
else
  fail_msg 'Docker Compose v2 is unavailable.'
fi

if command -v python3 >/dev/null 2>&1; then
  pyver=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')
  pyminor=$(python3 -c 'import sys; print(sys.version_info.major * 100 + sys.version_info.minor)')
  if [ "$pyminor" -eq 313 ]; then pass "Python: $pyver"; else fail_msg "Python: $pyver (RAGFlow 0.27.2 requires Python 3.13.x)"; fi
else
  fail_msg 'python3 is unavailable.'
fi

if command -v uv >/dev/null 2>&1; then pass "uv: $(uv --version | awk '{print $2}')"; else fail_msg 'uv is unavailable.'; fi

if command -v node >/dev/null 2>&1; then
  nodever=$(node --version | sed 's/^v//')
  if version_ge "$nodever" '18.20.4'; then pass "Node: $nodever"; else fail_msg "Node: $nodever (need >= 18.20.4)"; fi
else
  fail_msg 'Node.js is unavailable.'
fi

if command -v npm >/dev/null 2>&1; then pass "npm: $(npm --version)"; else fail_msg 'npm is unavailable.'; fi

if command -v sysctl >/dev/null 2>&1; then
  vm_map=$(sysctl -n vm.max_map_count 2>/dev/null || echo 0)
  if [ "$vm_map" -ge 262144 ] 2>/dev/null; then pass "vm.max_map_count: $vm_map"; else fail_msg "vm.max_map_count: $vm_map (need >= 262144 for Elasticsearch)"; fi
else
  warn_msg 'sysctl unavailable; verify vm.max_map_count manually if using Elasticsearch.'
fi

if command -v pkg-config >/dev/null 2>&1 && pkg-config --exists jemalloc 2>/dev/null; then
  pass 'jemalloc development metadata found.'
else
  warn_msg 'jemalloc was not detected. Source backend launch script expects it on Linux.'
fi

printf '%s\n' '--------------------------------------'
printf 'Result: %d blocking failure(s), %d warning(s).\n' "$fail" "$warn"

if [ "$fail" -ne 0 ]; then
  exit 1
fi
