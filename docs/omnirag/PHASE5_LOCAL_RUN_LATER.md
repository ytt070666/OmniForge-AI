# Phase 5 local/integration sequence — run later

Do not execute the research stack until the clean Phase-1 baseline results have
been collected and archived.

## 0. Preserve the clean baseline

Keep a separate untouched copy of the full project and baseline outputs. The
pre-local package intentionally ships with all reviewed core files unchanged.

## 1. Install the full project runtime

Use the RAGFlow project's supported dependency workflow/container image. Then
run:

```bash
python scripts/omnirag/phase5_runtime_contract_validate.py
```

Acceptance:

- RAGFlow `Graph.validate_component_parameters()` accepts the compiled TaskSpec;
- the external MCP SDK can construct the read-only reference server.

Also run Ruff once the project development tools are installed.

## 2. Apply research patches in strict order

```bash
python scripts/omnirag/phase2_apply_patch.py --apply
python scripts/omnirag/phase3_apply_patch.py --apply
python scripts/omnirag/phase4_apply_patch.py --apply
python scripts/omnirag/phase5_apply_patch.py --apply
```

Do not manually edit the integration owners before these scripts; each phase has
pre-hash guards.

## 3. Start the read-only reference MCP server

In a separate process, run:

```bash
python -m extensions.omnirag.mcp.reference_server
```

Use the URL/path printed by the installed FastMCP runtime. Do not assume a path
if the runtime reports another one.

The fixture exposes only:

- `lookup_device`
- `search_runbook`
- `calculate_availability`

## 4. Register/test the MCP server through RAGFlow

Use RAGFlow's existing MCP UI/API. The reviewed REST owner exposes:

```text
GET    /api/v1/mcp/servers
POST   /api/v1/mcp/servers
POST   /api/v1/mcp/servers/<id>/test
```

RAGFlow should perform discovery and persist the returned tool metadata. Verify
that the discovered tool annotations/input schemas match the reference server.

Do not put credentials into TaskSpec or committed JSON fixtures.

## 5. Native tool baseline first

Before enabling OmniRAG governance, create a RAGFlow Agent that has:

- the three reference MCP tools;
- at least one built-in read tool;
- separately, one write/execute-capable tool for **negative policy tests only**.

Keep the actual model and tool inventory fixed for all A/B runs.

Record native:

- visible tool-schema count;
- chosen tool;
- tool arguments;
- success/failure;
- model rounds;
- latency;
- token usage.

## 6. Enable Phase-5 governance conservatively

```bash
export OMNIRAG_TOOL_GOVERNANCE=1
export OMNIRAG_TOOL_ALLOWED_RISKS=read
export OMNIRAG_TOOL_ALLOW_DESTRUCTIVE=0
export OMNIRAG_TOOL_ALLOW_OPEN_WORLD=0
export OMNIRAG_TOOL_MAX_VISIBLE=6
export OMNIRAG_TOOL_MAX_CALLS=8
export OMNIRAG_TOOL_MAX_CALLS_PER_TOOL=3
```

Verify:

- only a relevant read subset is bound to the model;
- write/execute/unknown tools do not appear in the shortlist;
- an explicit `openWorldHint=true` tool is denied by default;
- a call outside the shortlist is rejected before native execution;
- invalid JSON-Schema arguments are rejected before native execution;
- call budgets terminate repeated calls;
- `_OMNIRAG_TOOL_TRACE` has keys/HMAC/error type but no raw argument values.

## 7. Contradictory-annotation adversarial test

Register a controlled test tool whose metadata says `readOnlyHint=true` while
its name/description is clearly destructive (for example `delete_records`). Do
**not** connect it to real destructive functionality.

Acceptance: Phase-5 risk classification must remain WRITE and default policy
must reject it.

This confirms annotations are not being used as authorization.

## 8. Open-world opt-in test

Only after the default-deny test passes:

```bash
export OMNIRAG_TOOL_ALLOW_OPEN_WORLD=1
```

Enable one benign read-only external tool and confirm it becomes eligible. Then
restore the default false value.

## 9. TaskSpec runtime validation and Canvas execution

Replace fixture placeholders with real tenant-owned IDs in a temporary local
copy:

- `REPLACE_WITH_DATASET_ID`
- `REPLACE_WITH_LLM_ID`

Compile:

```bash
python scripts/omnirag/phase5_compile_taskspec.py \
  --input /tmp/grounded_qa.local.json \
  --output /tmp/grounded_qa.canvas.json
```

Run native parameter validation, then import/execute through RAGFlow Canvas.
Acceptance:

- Retrieval receives the user query;
- Agent receives `${retrieve.formalized_content}` through the compiled native
  variable reference;
- Message emits `${answer.content}`;
- no generated raw MCP/tool definition appears in the DSL.

## 10. Runtime ablation matrix

With a fixed Agent/model/tool catalog, run at least:

| Run | Native tools | Phase-5 policy | Pre-selector | Execution guard |
|---|---:|---:|---:|---:|
| A | on | off | off | off |
| B | on | on | off* | on |
| C | on | on | on | on |

`*` If implementing a policy-only ablation, expose all policy-approved tools
without relevance ranking. Keep that implementation isolated from the final
selector.

Later optional run D can replace the deterministic selector with a semantic
router while keeping the exact same policy/execution guard.

## 11. Live metrics

Selection/safety:

- Top-1/Top-k tool selection accuracy on held-out tasks;
- policy-denial precision/recall;
- unsafe write/execute exposure rate;
- unnecessary-tool exposure count;
- model-visible schema count.

Execution/task quality:

- tool execution success rate;
- end-to-end task success rate;
- invalid-argument rate;
- budget-exhaustion rate;
- model rounds per task.

Efficiency:

- latency;
- prompt/completion tokens;
- tool-schema prompt tokens;
- MCP call latency.

Do not publish the ten-case synthetic smoke score as any of these live metrics.

## 12. Logging/privacy acceptance

Inspect actual service logs while a tool is called with a canary value. Although
OmniRAG's governance trace excludes raw values, upstream RAGFlow logging may
contain native tool arguments. Configure/redact production logs accordingly
before claiming privacy-safe tool auditing.

## 13. Phase-5 exit criteria

Phase 5 is locally accepted only when all of the following are true:

- runtime contract script passes;
- reference MCP server connects through RAGFlow;
- tools are discovered with expected schemas;
- governed read calls execute;
- write/execute/open-world negative cases are blocked as expected;
- schema/budget/shortlist guards are observed before native execution;
- TaskSpec is native-validated and executes in Canvas;
- live benchmark results are stored with model/tool/config versions;
- no frozen baseline result has been overwritten.
