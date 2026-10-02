#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

echo "[1/8] Compile Phase-4 extension and tooling"
python3 -m compileall -q extensions/omnirag/agent scripts/omnirag tests/omnirag

echo "[2/8] Deterministic contract scenarios"
python3 scripts/omnirag/phase4_contract_validate.py

echo "[3/8] OmniRAG unit tests"
python3 -m pytest -q tests/omnirag

echo "[4/8] Validate Phase-4 configuration"
python3 - <<'PY'
import json
from pathlib import Path
p = Path('config/omnirag/phase4_agent_governance.json')
cfg = json.loads(p.read_text(encoding='utf-8'))
assert cfg['phase'] == '4'
flags = cfg['feature_flags_default']
assert flags and all(value is False for value in flags.values())
assert cfg['memory']['factual_evidence'] is False
assert cfg['memory']['tenant_scope_required'] is True
print('PASS: Phase-4 defaults are disabled and memory is non-evidence/tenant-scoped')
PY

echo "[5/8] Earlier staged patches remain applicable to the frozen baseline"
python3 scripts/omnirag/phase2_apply_patch.py --check >/dev/null
python3 scripts/omnirag/phase3_apply_patch.py --check >/dev/null
echo "PASS: Phase-2 and Phase-3 patch checks"

echo "[6/8] Full Phase-2 -> Phase-3 -> Phase-4 patch stack"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/rag/nlp" "$TMP/api/db/services" "$TMP/rag/advanced_rag"
cp rag/nlp/search.py "$TMP/rag/nlp/search.py"
cp api/db/services/dialog_service.py "$TMP/api/db/services/dialog_service.py"
cp rag/advanced_rag/agentic_rag.py "$TMP/rag/advanced_rag/agentic_rag.py"
patch -s -p1 -d "$TMP" < patches/omnirag/phase2_adaptive_retrieval.patch
patch -s -p1 -d "$TMP" < patches/omnirag/phase3_multimodal_verifier.patch
patch -s -p1 -d "$TMP" < patches/omnirag/phase4_memory_agent_governance.patch
python3 -m py_compile "$TMP/rag/nlp/search.py" "$TMP/api/db/services/dialog_service.py" "$TMP/rag/advanced_rag/agentic_rag.py"
python3 - "$TMP" <<'PY'
from pathlib import Path
import hashlib
import sys
root = Path(sys.argv[1])
# These hashes document the exact post-patch syntax-tested outputs for this package.
for rel in ['rag/nlp/search.py', 'api/db/services/dialog_service.py', 'rag/advanced_rag/agentic_rag.py']:
    p = root / rel
    print(rel, hashlib.sha256(p.read_bytes()).hexdigest())
PY

echo "[7/8] Frozen Phase-1 core remains untouched in the deliverable tree"
python3 scripts/omnirag/phase1_verify_core_untouched.py

echo "[8/8] Patch scope guard"
python3 - <<'PY'
from pathlib import Path
patch = Path('patches/omnirag/phase4_memory_agent_governance.patch').read_text(encoding='utf-8')
paths = [line[6:] for line in patch.splitlines() if line.startswith('--- a/')]
assert paths == ['api/db/services/dialog_service.py', 'rag/advanced_rag/agentic_rag.py'], paths
assert 'terminal tool' in patch.lower()
print('PASS: Phase-4 core patch touches only the two reviewed integration owners')
PY

echo "Phase-4 static validation: PASS"
