#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

EXPECTED_SEARCH="5c96ad4364907378b4d579e5a0ec74be3b627f2616c96681198b6bcf1853534d"
EXPECTED_DIALOG="1c74b3d71a3778790c25b026ff00d69bedba96aea941ebb373fb2243e6425738"
EXPECTED_AGENTIC="9a4d6b951c064060be3b504b35bd34babe56ffd47346a88384a384d172b5a5ac"
EXPECTED_TOOLS="096520e7820b1412ea2d2707542d3ef9767d4b02d65cf5ac31e2f5d1b2469e63"

printf '%s\n' "[1/12] Compile Phase-5 extensions and tooling"
python3 -m compileall -q \
  extensions/omnirag/tools \
  extensions/omnirag/dsl \
  extensions/omnirag/mcp \
  scripts/omnirag \
  tests/omnirag

printf '%s\n' "[2/12] Deterministic Phase-5 contracts"
python3 scripts/omnirag/phase5_contract_validate.py

printf '%s\n' "[3/12] Full OmniRAG unit test suite"
python3 -m pytest -q tests/omnirag

printf '%s\n' "[4/12] Validate conservative Phase-5 configuration"
python3 - <<'PY'
import json
from pathlib import Path
cfg = json.loads(Path('config/omnirag/phase5_tool_governance.json').read_text(encoding='utf-8'))
assert str(cfg['phase']) == '5'
assert cfg['feature_flags_default']['OMNIRAG_TOOL_GOVERNANCE'] is False
assert cfg['tool_policy']['default_allowed_risks'] == ['read']
assert cfg['tool_policy']['allow_destructive_default'] is False
assert cfg['tool_policy']['allow_open_world_default'] is False
assert cfg['tool_policy']['argument_values_stored_in_audit_trace'] is False
assert cfg['tool_policy']['mcp_annotations_are_authorization'] is False
assert cfg['mcp']['transport_owner'] == 'RAGFlow'
assert cfg['mcp']['protocol_name'] == 'Model Context Protocol'
assert cfg['mcp']['new_transport_implementation_claimed'] is False
assert cfg['dsl']['runtime_owner'] == 'RAGFlow Canvas'
assert cfg['dsl']['generated_spec_executes_without_validation'] is False
assert cfg['dsl']['arbitrary_secret_value_detection_claimed'] is False
assert cfg['integration']['native_mcp_client_replaced'] is False
assert cfg['integration']['native_mcp_server_replaced'] is False
assert cfg['integration']['native_tool_executor_replaced'] is False
assert cfg['integration']['native_canvas_executor_replaced'] is False
print('PASS: Phase-5 defaults are opt-in, read-only, closed-world and native-runtime preserving')
PY

printf '%s\n' "[5/12] Synthetic tool-selector smoke benchmark"
python3 scripts/omnirag/phase5_evaluate_tool_selection.py
if [[ "$OSTYPE" == msys* ]]; then
  sed -i 's/\r$//' artifacts/omnirag/phase5_tool_selection_smoke.json
fi
python3 - <<'PY'
import json
from pathlib import Path
r = json.loads(Path('artifacts/omnirag/phase5_tool_selection_smoke.json').read_text(encoding='utf-8'))
assert r['cases'] == 10
assert r['top3'] == 1.0
print(f"PASS: synthetic smoke only (Top-1={r['top1']:.3f}, Top-3={r['top3']:.3f}); not an end-to-end Agent metric")
PY

printf '%s\n' "[6/12] TaskSpec validate/compile contract"
python3 scripts/omnirag/phase5_compile_taskspec.py \
  --input benchmarks/omnirag/phase5/taskspec_grounded_qa.json \
  --output artifacts/omnirag/phase5_grounded_qa.compiled.json >/dev/null
if [[ "$OSTYPE" == msys* ]]; then
  sed -i 's/\r$//' artifacts/omnirag/phase5_grounded_qa.compiled.json
fi
python3 - <<'PY'
import json
from pathlib import Path
dsl = json.loads(Path('artifacts/omnirag/phase5_grounded_qa.compiled.json').read_text(encoding='utf-8'))
assert set(dsl['components']) == {'begin', 'Retrieval:Omni_retrieve', 'Agent:Omni_answer', 'Message:Omni_respond'}
assert dsl['retrieval'] == []
rag_node = next(n for n in dsl['graph']['nodes'] if n['id'] == 'Retrieval:Omni_retrieve')
assert rag_node['type'] == 'ragNode'
assert dsl['components']['Agent:Omni_answer']['obj']['params']['mcp'] == []
assert dsl['components']['Agent:Omni_answer']['obj']['params']['tools'] == []
print('PASS: TaskSpec compiles to restricted native Canvas-shaped DSL without raw tool/MCP injection')
PY

printf '%s\n' "[7/12] Staged patch checks"
python3 scripts/omnirag/phase2_apply_patch.py --check >/dev/null
python3 scripts/omnirag/phase3_apply_patch.py --check >/dev/null
python3 scripts/omnirag/phase5_apply_patch.py --check >/dev/null
printf '%s\n' "PASS: Phase-2/3/5 standalone checks pass; Phase-4 requires the Phase-3 state and is verified in the full ordered stack below"

printf '%s\n' "[8/12] Full Phase-2 -> Phase-3 -> Phase-4 -> Phase-5 patch stack"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/rag/nlp" "$TMP/api/db/services" "$TMP/rag/advanced_rag" "$TMP/agent/component"
cp rag/nlp/search.py "$TMP/rag/nlp/search.py"
cp api/db/services/dialog_service.py "$TMP/api/db/services/dialog_service.py"
cp rag/advanced_rag/agentic_rag.py "$TMP/rag/advanced_rag/agentic_rag.py"
cp agent/component/agent_with_tools.py "$TMP/agent/component/agent_with_tools.py"
patch -s -p1 -d "$TMP" < patches/omnirag/phase2_adaptive_retrieval.patch
patch -s -p1 -d "$TMP" < patches/omnirag/phase3_multimodal_verifier.patch
patch -s -p1 -d "$TMP" < patches/omnirag/phase4_memory_agent_governance.patch
patch -s -p1 -d "$TMP" < patches/omnirag/phase5_tool_governance.patch
python3 -m py_compile \
  "$TMP/rag/nlp/search.py" \
  "$TMP/api/db/services/dialog_service.py" \
  "$TMP/rag/advanced_rag/agentic_rag.py" \
  "$TMP/agent/component/agent_with_tools.py"
python3 - "$TMP" "$EXPECTED_SEARCH" "$EXPECTED_DIALOG" "$EXPECTED_AGENTIC" "$EXPECTED_TOOLS" <<'PY'
import hashlib
import sys
from pathlib import Path
root = Path(sys.argv[1])
expected = {
    'rag/nlp/search.py': sys.argv[2],
    'api/db/services/dialog_service.py': sys.argv[3],
    'rag/advanced_rag/agentic_rag.py': sys.argv[4],
    'agent/component/agent_with_tools.py': sys.argv[5],
}
for rel, digest in expected.items():
    actual = hashlib.sha256((root / rel).read_bytes()).hexdigest()
    if actual != digest:
        raise SystemExit(f'post-patch hash mismatch for {rel}: {actual} != {digest}')
    print(rel, actual)
print('PASS: full patch stack compiles and matches reviewed post-patch hashes')
PY

printf '%s\n' "[9/12] Frozen Phase-1 core remains untouched"
python3 scripts/omnirag/phase1_verify_core_untouched.py
python3 - <<'PY'
from pathlib import Path
import hashlib
p = Path('agent/component/agent_with_tools.py')
actual = hashlib.sha256(p.read_bytes()).hexdigest()
expected = '181fdb3f2307be50ef18a031b75bcefb4403dc8d706bada63843bd07f480998e'
assert actual == expected, (actual, expected)
print('PASS: Agent tool integration owner is also still at the reviewed pre-Phase-5 hash')
PY

printf '%s\n' "[10/12] Patch scope and ownership guard"
python3 - <<'PY'
from pathlib import Path
patch = Path('patches/omnirag/phase5_tool_governance.patch').read_text(encoding='utf-8')
paths = [line[6:] for line in patch.splitlines() if line.startswith('--- a/')]
assert paths == ['agent/component/agent_with_tools.py'], paths
assert 'extensions.omnirag.tools.integration' in patch
cfg = Path('config/omnirag/phase5_tool_governance.json').read_text(encoding='utf-8')
assert 'RAGFlow Canvas' in cfg and 'Model Context Protocol' in cfg
print('PASS: Phase-5 patch touches only the reviewed Agent binding hook; RAGFlow retains MCP/Canvas ownership')
PY

printf '%s\n' "[11/12] Runtime-only dependency contract status"
python3 - <<'PY'
mods = ('quart', 'json_repair', 'peewee')
missing = []
for name in mods:
    try:
        __import__(name)
    except Exception:
        missing.append(name)
if missing:
    print('DEFERRED (expected pre-local): native Graph.validate_component_parameters/runtime MCP contract needs full RAGFlow env; missing=' + ','.join(missing))
else:
    print('Runtime dependencies appear present; execute: python3 scripts/omnirag/phase5_runtime_contract_validate.py')
PY
if command -v ruff >/dev/null 2>&1; then
  ruff check extensions/omnirag/tools extensions/omnirag/dsl extensions/omnirag/mcp scripts/omnirag/phase5_*.py tests/omnirag/*phase5*.py
else
  printf '%s\n' "DEFERRED: ruff executable is not installed in this pre-local environment"
fi

printf '%s\n' "[12/12] Phase-5 manifest file integrity"
python3 - <<'PY'
import hashlib
import json
from pathlib import Path
root = Path('.')
manifest = json.loads(Path('docs/omnirag/PHASE5_MANIFEST.json').read_text(encoding='utf-8'))
assert manifest['validation']['omnirag_unit_tests_passed'] == 56
for row in manifest['files']:
    p = root / row['path']
    assert p.exists(), row['path']
    actual = hashlib.sha256(p.read_bytes()).hexdigest()
    assert actual == row['sha256'], (row['path'], actual, row['sha256'])
print(f"PASS: {len(manifest['files'])} Phase-5 manifest file hashes match")
PY

printf '%s\n' "Phase-5 static validation: PASS (runtime-only contracts explicitly deferred, not claimed)"
