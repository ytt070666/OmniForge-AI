# Phase 5 acceptance checklist

## Pre-local (completed)

- [x] Source ownership review: RAGFlow owns MCP transport/tool execution/Canvas.
- [x] Phase-5 core patch restricted to one Agent binding owner.
- [x] Feature flag defaults off.
- [x] READ-only default policy.
- [x] Open-world default deny.
- [x] MCP annotations treated as advisory only.
- [x] Per-query shortlist implemented.
- [x] Schema and call-budget enforcement implemented.
- [x] Privacy-reduced OmniRAG audit trace implemented.
- [x] Restricted TaskSpec parser/validator/compiler implemented.
- [x] Generated TaskSpec cannot inject raw MCP/tools.
- [x] Read-only reference MCP fixture implemented.
- [x] Full OmniRAG tests pass.
- [x] Ordered Phase-2/3/4/5 patch stack compiles in isolation.
- [x] Frozen baseline remains unchanged.

## Deferred until full local runtime

- [ ] RAGFlow native Graph parameter validation on compiled TaskSpec.
- [ ] FastMCP construction under the actual project SDK version.
- [ ] Streamable HTTP MCP connection through RAGFlow.
- [ ] MCP tool discovery through `/api/v1/mcp/servers`.
- [ ] Live LLM tool-calling baseline.
- [ ] Governance A/B run.
- [ ] Adversarial contradictory-annotation live fixture.
- [ ] Open-world opt-in live check.
- [ ] Canvas execution of compiled TaskSpec.
- [ ] Held-out live selection/task benchmark.
- [ ] Native logging/redaction review.
- [ ] Ruff in project development environment.
