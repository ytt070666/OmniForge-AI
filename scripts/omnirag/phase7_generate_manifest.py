#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'docs/omnirag/PHASE7_MANIFEST.json'
OWNED=[
 '.github/workflows/omnirag-ci.yml',
 'config/omnirag/phase7',
 'deploy/omnirag',
 'extensions/omnirag/product',
 'scripts/omnirag/phase7_build_dashboard.py',
 'scripts/omnirag/phase7_generate_manifest.py',
 'scripts/omnirag/phase7_static_validate.py',
 'scripts/omnirag/phase7_verify_runtime_source.py',
 'docs/omnirag/PHASE7_ENGINEERING_PRODUCTIZATION.md',
 'docs/omnirag/PHASE7_LOCAL_RUN_LATER.md',
 'docs/omnirag/PORTFOLIO_README.md',
 'docs/omnirag/PHASE7_PRELOCAL_REPORT.md',
 'artifacts/omnirag/phase7',
]
def sha(p:Path)->str: return hashlib.sha256(p.read_bytes()).hexdigest()
def files_for(x:str):
 p=ROOT/x
 if p.is_dir(): return sorted(q for q in p.rglob('*') if q.is_file() and '__pycache__' not in q.parts)
 return [p] if p.exists() else []
def main():
 files=[]
 for x in OWNED: files.extend(files_for(x))
 seen=set(); rows=[]
 for p in sorted(files):
  rel=str(p.relative_to(ROOT))
  if rel in seen or rel==str(OUT.relative_to(ROOT)): continue
  seen.add(rel); rows.append({'path':rel,'bytes':p.stat().st_size,'sha256':sha(p)})
 payload={
  'phase':7,'release_stage':'prelocal_ready','runtime_verified':False,
  'baseline_core_state':'frozen_unmodified',
  'container_build':'not_run_in_current_environment_docker_unavailable',
  'kubernetes_apply':'not_run_in_current_environment_kubectl_unavailable',
  'live_metrics_policy':'missing live artifacts remain not_run',
  'files':rows,
 }
 OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
 print(f'wrote {OUT} ({len(rows)} files)')
if __name__=='__main__': main()
