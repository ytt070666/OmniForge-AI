# Local runbook — execute later, after offline preparation is complete

This file is a runbook, not evidence that the stack has already been executed.

## 1. Choose profile

Start with `research_balanced`. If the local machine cannot serve the 8B VLM concurrently with RAGFlow, keep the same model name but point `OMNIRAG_CHAT_BASE_URL` to a remote OpenAI-compatible endpoint for the first baseline. Retrieval metrics remain valid as long as the embedding baseline is unchanged.

## 2. Prepare environment

Copy the variables from `docker/omnirag/.env.baseline.example` into a local, ignored environment file. Replace every `CHANGE_ME`. Keep:

```text
OMNIRAG_ADAPTIVE_RETRIEVAL=0
OMNIRAG_EVIDENCE_VERIFIER=0
OMNIRAG_MEMORY_POLICY=0
```

## 3. Baseline order

Run `check_phase1_env.sh`, then start the RAGFlow stack, configure the model provider, run `phase1_smoke.sh`, and finally run `phase1_acceptance.sh`.

The acceptance runner creates a deterministic retrieval report. Do not apply the Phase-2 patch until the report and `run_manifest.json` are copied into an immutable results folder or tagged commit.

## 4. Phase 2 order

After baseline archival:

```bash
python3 scripts/omnirag/phase2_apply_patch.py --check
python3 scripts/omnirag/phase2_apply_patch.py --apply
export OMNIRAG_ADAPTIVE_RETRIEVAL=1
```

Then run three ablations by changing:

```text
OMNIRAG_ADAPTIVE_CANDIDATE
OMNIRAG_ADAPTIVE_FINAL
```

Do not enable the evidence verifier or memory policy until retrieval ablations are finished.
