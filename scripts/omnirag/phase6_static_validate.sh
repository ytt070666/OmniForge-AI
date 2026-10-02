#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

printf '%s\n' "[1/12] Rebuild deterministic Phase-6 dataset"
python3 scripts/omnirag/phase6_build_router_dataset.py >/dev/null

printf '%s\n' "[2/12] Compile Phase-6 code"
python3 -m compileall -q \
  extensions/omnirag/training \
  extensions/omnirag/observability \
  scripts/omnirag/phase6_*.py \
  tests/omnirag/test_training_phase6.py \
  tests/omnirag/test_observability_phase6.py

printf '%s\n' "[3/12] Deterministic Phase-6 contracts"
python3 scripts/omnirag/phase6_contract_validate.py

printf '%s\n' "[4/12] Full OmniRAG unit suite"
python3 -m pytest -q tests/omnirag

printf '%s\n' "[5/12] Training preflight without download"
python3 scripts/omnirag/phase6_train_router.py --preflight-only >/dev/null
printf '%s\n' "PASS: training config/data can be validated without model download"

printf '%s\n' "[6/12] Rule-router baselines are reproducible"
python3 scripts/omnirag/phase6_rule_baseline.py \
  --dataset benchmarks/omnirag/phase6/router/test.jsonl \
  --output artifacts/omnirag/phase6/rule_baseline_test_predictions.jsonl >/dev/null
python3 scripts/omnirag/phase6_evaluate_router.py \
  --dataset benchmarks/omnirag/phase6/router/test.jsonl \
  --predictions artifacts/omnirag/phase6/rule_baseline_test_predictions.jsonl \
  --output artifacts/omnirag/phase6/rule_baseline_test_metrics.json >/dev/null
python3 scripts/omnirag/phase6_rule_baseline.py \
  --dataset benchmarks/omnirag/phase6/router/protected_benchmark.jsonl \
  --output artifacts/omnirag/phase6/rule_baseline_protected_predictions.jsonl >/dev/null
python3 scripts/omnirag/phase6_evaluate_router.py \
  --dataset benchmarks/omnirag/phase6/router/protected_benchmark.jsonl \
  --predictions artifacts/omnirag/phase6/rule_baseline_protected_predictions.jsonl \
  --output artifacts/omnirag/phase6/rule_baseline_protected_metrics.json >/dev/null
python3 scripts/omnirag/phase6_contract_validate.py >/dev/null
printf '%s\n' "PASS: rule-router baseline artifacts reproduce the reviewed metrics"

printf '%s\n' "[7/12] Promotion gate is fail-closed"
python3 scripts/omnirag/phase6_promotion_gate.py --check-config-only
if python3 scripts/omnirag/phase6_promotion_gate.py >/tmp/omnirag_phase6_gate.out 2>&1; then
  printf '%s\n' "ERROR: promotion gate unexpectedly passed without learned metrics" >&2
  exit 1
else
  grep -q "NOT_RUN" /tmp/omnirag_phase6_gate.out
  printf '%s\n' "PASS: missing learned metrics remain NOT_RUN"
fi
rm -f /tmp/omnirag_phase6_gate.out

printf '%s\n' "[8/12] Observability fixture and no-invented-cost contract"
python3 scripts/omnirag/phase6_aggregate_observability.py \
  --events benchmarks/omnirag/phase6/observability_fixture.jsonl \
  --output artifacts/omnirag/phase6/observability_fixture_summary.json >/dev/null
python3 - <<'PY'
import json
from pathlib import Path
r=json.loads(Path('artifacts/omnirag/phase6/observability_fixture_summary.json').read_text())
assert r['events']==3
assert r['cost'] is None
assert r['tools']['calls']==1 and r['tools']['failures']==1
print('PASS: observability aggregation does not invent provider cost')
PY

printf '%s\n' "[9/12] Evaluation matrix never fabricates missing live metrics"
python3 scripts/omnirag/phase6_collect_evaluation_matrix.py >/dev/null
python3 - <<'PY'
import json
from pathlib import Path
m=json.loads(Path('artifacts/omnirag/phase6/evaluation_matrix.json').read_text())
by={x['name']:x for x in m['evaluations']}
assert by['phase6_learned_router_test']['status']=='not_run'
assert by['phase6_learned_router_protected']['status']=='not_run'
assert by['phase6_system_observability']['status']=='not_run'
print('PASS: missing live/training artifacts are explicitly not_run')
PY

printf '%s\n' "[10/12] Prior Phase-5 contracts and patch stack remain valid"
python3 scripts/omnirag/phase5_contract_validate.py >/dev/null
python3 - <<'PY2'
import hashlib, json
from pathlib import Path
root=Path('.')
m=json.loads(Path('docs/omnirag/PHASE5_MANIFEST.json').read_text())
for row in m['files']:
    p=root/row['path']
    assert p.exists(), row['path']
    assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'], row['path']
print('PASS: Phase-5 manifest files remain unchanged')
PY2
TMP="$(mktemp -d)"
mkdir -p "$TMP/rag/nlp" "$TMP/api/db/services" "$TMP/rag/advanced_rag" "$TMP/agent/component"
cp rag/nlp/search.py "$TMP/rag/nlp/search.py"
cp api/db/services/dialog_service.py "$TMP/api/db/services/dialog_service.py"
cp rag/advanced_rag/agentic_rag.py "$TMP/rag/advanced_rag/agentic_rag.py"
cp agent/component/agent_with_tools.py "$TMP/agent/component/agent_with_tools.py"
patch -s -p1 -d "$TMP" < patches/omnirag/phase2_adaptive_retrieval.patch
patch -s -p1 -d "$TMP" < patches/omnirag/phase3_multimodal_verifier.patch
patch -s -p1 -d "$TMP" < patches/omnirag/phase4_memory_agent_governance.patch
patch -s -p1 -d "$TMP" < patches/omnirag/phase5_tool_governance.patch
python3 -m py_compile "$TMP/rag/nlp/search.py" "$TMP/api/db/services/dialog_service.py" "$TMP/rag/advanced_rag/agentic_rag.py" "$TMP/agent/component/agent_with_tools.py"
rm -rf "$TMP"
printf '%s\n' "PASS: Phase-5 contracts, manifest and ordered patch stack remain valid"

printf '%s\n' "[11/12] Frozen core and no Phase-6 patch"
python3 scripts/omnirag/phase1_verify_core_untouched.py >/dev/null
test ! -e patches/omnirag/phase6_posttraining.patch
printf '%s\n' "PASS: Phase-6 does not modify RAGFlow core"

printf '%s\n' "[12/12] Phase-6 manifest integrity"
python3 - <<'PY'
import hashlib, json
from pathlib import Path
root=Path('.')
manifest=json.loads(Path('docs/omnirag/PHASE6_MANIFEST.json').read_text())
assert manifest['validation']['omnirag_unit_tests_passed']==66
for row in manifest['files']:
    p=root/row['path']
    assert p.exists(), row['path']
    digest=hashlib.sha256(p.read_bytes()).hexdigest()
    assert digest==row['sha256'], (row['path'],digest,row['sha256'])
print(f"PASS: {len(manifest['files'])} Phase-6 file hashes match")
PY

if command -v ruff >/dev/null 2>&1; then
  ruff check extensions/omnirag/training extensions/omnirag/observability scripts/omnirag/phase6_*.py tests/omnirag/*phase6*.py
else
  printf '%s\n' "DEFERRED: ruff executable is not installed in this pre-local environment"
fi

printf '%s\n' "Phase-6 static validation: PASS (model training/live metrics explicitly deferred, not claimed)"
