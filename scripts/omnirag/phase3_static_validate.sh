#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

echo "[1/7] Compile OmniRAG Phase-3 Python"
python3 -m compileall -q extensions/omnirag scripts/omnirag

echo "[2/7] Validate benchmark assets"
python3 - <<'PY'
import json
from pathlib import Path
p=Path('benchmarks/omnirag/phase3')
assets=sorted((p/'assets').glob('*.png'))
records=[json.loads(x) for x in (p/'visual_records.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
queries=[json.loads(x) for x in (p/'queries.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
assert len(assets)==6, len(assets)
assert len(records)==6, len(records)
assert len(queries)==18, len(queries)
assert all((p/'assets'/r['asset']).exists() for r in records)
print(f'PASS: {len(assets)} images / {len(queries)} queries')
PY

echo "[3/7] Unit tests"
pytest -q tests/omnirag/test_adaptive_policy.py tests/omnirag/test_multimodal_phase3.py tests/omnirag/test_evidence_verifier_phase3.py

echo "[4/7] Phase-2 patch remains applicable"
python3 scripts/omnirag/phase2_apply_patch.py --check >/dev/null

echo "[5/7] Phase-3 patch remains applicable"
python3 scripts/omnirag/phase3_apply_patch.py --check >/dev/null

echo "[6/7] Baseline core remains untouched"
python3 scripts/omnirag/phase1_verify_core_untouched.py

echo "[7/7] Plumbing-only visual index build"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
OMNIRAG_VISUAL_ENCODER=hash python3 scripts/omnirag/phase3_build_visual_index.py --source benchmark --encoder hash --output "$TMP/index.jsonl" >/dev/null
python3 - "$TMP/index.jsonl" <<'PY'
import sys
from extensions.omnirag.multimodal.visual_index import JsonlVisualIndex
idx=JsonlVisualIndex(sys.argv[1])
assert len(idx.records()) == 6
print('PASS: visual sidecar index plumbing')
PY

echo "Phase-3 static validation: PASS"
