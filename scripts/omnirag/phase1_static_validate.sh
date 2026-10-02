#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$repo_root"

echo '[1/9] Python syntax validation'
python3 -m compileall -q api rag agent memory mcp common scripts/omnirag extensions/omnirag

echo '[2/9] Shell syntax validation'
bash -n docker/launch_backend_service.sh docker/entrypoint.sh build.sh scripts/omnirag/check_phase1_env.sh scripts/omnirag/phase1_bootstrap.sh scripts/omnirag/phase1_smoke.sh scripts/omnirag/phase1_acceptance.sh

echo '[3/9] Frontend manifest validation'
node -e "const p=require('./web/package.json'); if(!p.scripts?.dev || !p.scripts?.build) process.exit(1); console.log('web package:', p.version)"

echo '[4/9] Baseline version validation'
python3 - <<'PY'
import pathlib, re
text = pathlib.Path('pyproject.toml').read_text(encoding='utf-8')
m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
assert m and m.group(1) == '0.27.2', m.group(1) if m else 'missing'
print('RAGFlow version:', m.group(1))
PY

echo '[5/9] Deterministic benchmark validation'
python3 scripts/omnirag/phase1_collect_baseline.py --dry-run >/tmp/omnirag_phase1_dry_run.json
python3 - <<'PY'
import json
from pathlib import Path
rows = [json.loads(x) for x in Path('benchmarks/omnirag/phase1/queries.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
ids = [r['id'] for r in rows]
assert len(rows) == 28, len(rows)
assert len(ids) == len(set(ids)), 'duplicate query ids'
corpus = {p.name for p in Path('benchmarks/omnirag/phase1/corpus').iterdir() if p.is_file()}
missing = sorted({r['expected_document'] for r in rows} - corpus)
assert not missing, missing
print('queries:', len(rows), 'corpus files:', len(corpus))
PY

echo '[6/9] OmniRAG configuration validation'
python3 scripts/omnirag/validate_omnirag_configs.py

echo '[7/9] Adaptive policy offline preview'
python3 scripts/omnirag/phase2_policy_preview.py >/tmp/omnirag_phase2_policy_preview.log

echo '[8/9] Phase-2 patch dry-run against frozen source'
python3 scripts/omnirag/phase2_apply_patch.py --check

echo '[9/9] Core source integrity validation'
python3 scripts/omnirag/phase1_verify_core_untouched.py

echo 'Phase-1/pre-local static validation: PASS'
