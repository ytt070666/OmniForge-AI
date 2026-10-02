# OmniRAG-Agent Phase-3 Pre-local Report

## Completed without starting RAGFlow services

- Added joint text-image retrieval boundary under `extensions/omnirag/multimodal/`.
- Added deterministic query modality router.
- Added weighted reciprocal-rank fusion with cross-modal agreement bonus.
- Added retrieval-to-generation image bridge so retrieved pixels can reach the configured VLM, not just VLM-generated captions.
- Added persistent JSONL visual sidecar index with dataset/document filtering.
- Added optional lazy SigLIP2 encoder and a test-only deterministic encoder.
- Added REST-based visual index builder that can later pull RAGFlow chunk images.
- Added deterministic claim/evidence verifier and semantic-judge contract.
- Added SHA-guarded Phase-3 `dialog_service.py` patch; it is **not applied**.
- Added 6-image / 18-query multimodal benchmark.
- Added Phase-3 collection/evaluation/ablation scripts.
- Added unit tests and static validation.

## Deliberately not done yet

- No Docker/RAGFlow service startup.
- No model download.
- No GPU/CUDA dependency pinning.
- No real SigLIP2/Qwen inference.
- No Phase-2 or Phase-3 patch applied to the frozen baseline.
- No research metric is fabricated from the test-only hash encoder.

The project is therefore ready for a later controlled local run while preserving
a clean upstream baseline.
