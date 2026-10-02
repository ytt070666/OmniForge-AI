# Phase 7 Local Run Later

When a suitable machine is available, execute in this order:

1. Re-run all pre-local validation:
   `python scripts/omnirag/phase7_static_validate.py`
2. Copy `config/omnirag/phase7/omnirag.env.example` to a local untracked environment file and add credentials only outside Git.
3. Build the reviewed image:
   `docker build -f deploy/omnirag/Dockerfile -t omnirag-agent:phase7 .`
4. Run the original RAGFlow baseline first, with all `OMNIRAG_*` feature flags disabled.
5. Collect Phase 1 baseline artifacts.
6. Enable Phase 2 only; run retrieval ablations.
7. Enable Phase 3 only after the visual index/model dependencies are configured; run multimodal tests.
8. Enable Phase 4 governance; verify bounded retry, abstention, and memory tenant isolation.
9. Enable Phase 5 tool governance; run the reference MCP server and verify fail-closed behavior.
10. Train/evaluate Phase 6 router. Do not integrate it unless the promotion gate passes.
11. Only after live artifacts exist, rebuild `artifacts/omnirag/phase6/evaluation_matrix.json` and run `phase7_build_dashboard.py`.
12. Kubernetes comes last, after a successful single-host runtime and resource measurements.

No phase may inherit performance claims from synthetic/offline smoke tests.
