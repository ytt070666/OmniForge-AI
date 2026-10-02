# OmniRAG-Agent Phase 5 pre-local report

## Status

Phase 5 is **pre-local code-complete** for governed Tool Calling, MCP integration
fixtures, and restricted workflow authoring. No RAGFlow services, live model,
remote MCP transport, database, or Canvas execution was started in this phase.

## Source-driven design decisions

Source review confirmed that RAGFlow 0.27.2 already provides MCP client/server
infrastructure, Agent tool binding/execution, and Canvas DSL execution. Phase 5
therefore does not duplicate or relabel those upstream capabilities as OmniRAG
innovations.

The actual additions are:

- normalized built-in/MCP tool registry;
- conservative risk classification;
- read-only/closed-world default policy;
- deterministic per-query shortlist;
- execution allowlist + JSON-Schema + budget guard;
- privacy-reduced governance audit events;
- deterministic read-only external MCP fixture;
- restricted TaskSpec -> native Canvas compiler;
- one feature-flagged Agent binding hook.

## Security/correctness corrections made during Phase 5

1. MCP annotations are treated as advisory, not authorization.
2. A `readOnlyHint=true` cannot downgrade a delete/write/code-looking tool.
3. Open-world tools are denied by default and require explicit opt-in.
4. TaskSpec no longer silently skips malformed steps or coerces invalid
   dependency types.
5. TaskSpec rejects unknown authoring fields, invalid parameter types/bounds, and
   references to nonexistent component outputs.
6. Generated TaskSpec cannot insert raw MCP/tool configuration.
7. Empty tool shortlists explicitly clear stale provider bindings.
8. Disabling governance after an enabled turn restores the original native tool
   binding.
9. Audit fingerprints now use HMAC-SHA256 with an ephemeral per-session key
   rather than raw SHA-256 of argument values.
10. Governance audit errors store exception type rather than raw exception text.
11. JSON-Schema validation errors are sanitized to avoid echoing rejected values.

## Offline validation result

At package build time:

- Phase-5 deterministic contract script: **11 assertions PASS**;
- full OmniRAG test suite (Phase 2/3/4/5): **56 tests PASS**;
- Phase-5 specific tests are included in that total;
- synthetic tool-selection smoke set: **10 cases, Top-1=1.0, Top-3=1.0**;
- TaskSpec fixture validation/compilation: **PASS**;
- Phase-2 -> Phase-3 -> Phase-4 -> Phase-5 patch stack: **applied and
  syntax-compiled in an isolated temp tree**;
- post-patch hashes matched the reviewed values;
- Phase-1 protected core: **8/8 unchanged**;
- `agent/component/agent_with_tools.py` remains at its reviewed pre-Phase-5 hash
  in the deliverable tree;
- Phase-5 patch scope: **one core integration owner only**.

The selector result is explicitly a tiny synthetic smoke result; it is not an
Agent task-success metric.

## Deferred checks, not hidden failures

The current pre-local Python environment does not include the complete RAGFlow
runtime dependency set (`quart`, `json_repair`, `peewee`). Therefore the
following are **DEFERRED**:

- `Graph.validate_component_parameters()` over the generated TaskSpec DSL;
- actual Canvas execution;
- external MCP SDK/server construction inside the final project environment;
- Streamable HTTP MCP discovery/call through RAGFlow;
- live LLM tool calling.

A runtime contract script is included for these checks after dependencies are
installed.

`ruff` is also not available in the current environment. No Ruff PASS is
claimed.

## Important logging boundary

OmniRAG's own governance trace omits raw argument values. RAGFlow's native tool
execution path has existing logging that may include tool arguments. Phase 5
does not claim to override all upstream logging. Production redaction/log-level
review remains a local-deployment acceptance item.

## No performance claims yet

No claim is made yet about:

- tool-selection improvement on a held-out real benchmark;
- end-to-end task success;
- MCP reliability;
- latency/token overhead;
- unsafe-call reduction in production;
- workflow execution success.

Those require the later live run with fixed models, tool inventory, and test
cases.
