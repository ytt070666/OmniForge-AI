#!/usr/bin/env python3
"""Generate the server restart / collection plan for Phase-2 ablations."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "omnirag" / "prelocal" / "PHASE2_ABLATION_COMMANDS.txt"

TEXT = r'''# Execute only after Phase-1 baseline has been archived and Phase-2 patch applied.
# Each block changes server-side environment variables, so restart the RAGFlow
# backend/container before running its collector.

# A. Final fusion only
export OMNIRAG_ADAPTIVE_RETRIEVAL=1
export OMNIRAG_ADAPTIVE_CANDIDATE=0
export OMNIRAG_ADAPTIVE_FINAL=1
# restart RAGFlow backend here
python3 scripts/omnirag/phase2_collect_adaptive.py --run-label final_only
python3 scripts/omnirag/phase2_evaluate_adaptive.py

# B. Candidate acquisition only
export OMNIRAG_ADAPTIVE_RETRIEVAL=1
export OMNIRAG_ADAPTIVE_CANDIDATE=1
export OMNIRAG_ADAPTIVE_FINAL=0
# restart RAGFlow backend here
python3 scripts/omnirag/phase2_collect_adaptive.py --run-label candidate_only
python3 scripts/omnirag/phase2_evaluate_adaptive.py

# C. Full two-stage policy
export OMNIRAG_ADAPTIVE_RETRIEVAL=1
export OMNIRAG_ADAPTIVE_CANDIDATE=1
export OMNIRAG_ADAPTIVE_FINAL=1
# restart RAGFlow backend here
python3 scripts/omnirag/phase2_collect_adaptive.py --run-label two_stage
python3 scripts/omnirag/phase2_evaluate_adaptive.py
'''

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(TEXT, encoding="utf-8")
print(OUT)
