# OmniRAG-Agent Phase 5 — Governed Tools, MCP Integration, and Safe TaskSpec

## 1. Purpose

Phase 5 addresses the job-facing capabilities around Tool Calling, MCP,
Client/Server integration, and workflow/DSL authoring without misrepresenting
capabilities that already belong to RAGFlow 0.27.2.

The Phase-5 contribution is **not** a new MCP protocol implementation and **not**
a second workflow runtime. Source review shows that RAGFlow already owns:

- MCP client transport and sessions;
- MCP server APIs;
- conversion of MCP tool metadata to model function schemas;
- built-in/MCP tool invocation;
- iterative model tool-calling;
- Agent Canvas execution and workflow DSL.

OmniRAG Phase 5 therefore adds a conservative control and authoring layer around
those existing owners.

All Phase-5 runtime behavior is opt-in and disabled by default.

---

## 2. Exact ownership boundary

### RAGFlow remains responsible for

- MCP transport and connection lifecycle;
- MCP server CRUD/import/test APIs;
- MCP tool discovery;
- built-in tool execution;
- MCP tool execution;
- model provider tool-call loop;
- Agent Canvas execution;
- native component implementations.

### OmniRAG Phase 5 is responsible for

1. normalizing built-in and MCP tools into one auditable registry;
2. conservative tool-risk classification;
3. per-query policy filtering and shortlist selection;
4. execution-time allowlist/schema/budget enforcement;
5. privacy-reduced governance traces;
6. a deterministic read-only MCP fixture used later for integration tests;
7. a restricted TaskSpec authoring language that compiles into native Canvas DSL;
8. preventing generated TaskSpec from injecting raw MCP/tool definitions.

This separation is intentional: it keeps the research contribution measurable
and minimizes divergence from upstream RAGFlow.

---

## 3. Tool-governance architecture

```text
Configured RAGFlow Agent
        |
        | built-in tools + MCP bindings
        v
OmniRAG ToolRegistry
        |
        +--> normalize schema/source/server/hints
        |
        v
Conservative ToolPolicy
        |
        +--> default allowed risk: READ only
        +--> destructive: deny
        +--> explicit open-world: deny
        +--> UNKNOWN: deny
        |
        v
ToolSelectorV1
        |
        +--> deterministic capability score
        +--> bounded model-visible shortlist
        |
        v
RAGFlow model bind_tools(...)
        |
        v
LLM final tool choice
        |
        v
GovernedToolCallSession
        |
        +--> selected-tool allowlist
        +--> policy re-check
        +--> JSON-Schema validation
        +--> total/per-tool call budget
        +--> audit event
        |
        v
RAGFlow native ToolCallSession
        |
        +--> built-in tool OR MCP tool
```

The selector is a **pre-selector** only. It does not claim to replace the
model's final tool choice.

---

## 4. MCP annotations are hints, not authorization

Phase 5 stores the standard MCP annotations when RAGFlow has persisted them, but
never treats them as a security boundary.

A contradictory server can claim:

```json
{"readOnlyHint": true, "destructiveHint": false}
```

for a tool named `delete_records`. The Phase-5 classifier still assigns WRITE
risk because lexical write/execute evidence takes precedence over the advisory
read-only hint.

Conservative risk order:

1. `destructiveHint=true` -> WRITE;
2. execute/code/shell/sql/browser indicators -> EXECUTE;
3. create/update/delete/write/send/upload indicators -> WRITE;
4. clear read/search/get/list/query indicators -> READ;
5. only if no risky lexical evidence exists may `readOnlyHint=true` serve as a
   weak READ hint;
6. otherwise -> UNKNOWN.

Default policy permits only READ. WRITE, EXECUTE, and UNKNOWN remain denied
unless explicitly enabled by the operator.

---

## 5. Closed-world default

The default is intentionally enterprise-conservative:

```text
OMNIRAG_TOOL_ALLOWED_RISKS=read
OMNIRAG_TOOL_ALLOW_DESTRUCTIVE=0
OMNIRAG_TOOL_ALLOW_OPEN_WORLD=0
```

An MCP tool carrying `openWorldHint=true` is rejected by default. Operators may
explicitly enable open-world read tools later after network/data-governance
review.

A missing `openWorldHint` is not proof that a tool is closed-world. For this
reason live acceptance must also review the actual server/tool inventory; the
annotation alone is not sufficient assurance.

---

## 6. Dynamic shortlist

`ToolSelectorV1` uses a deterministic, inspectable score over:

- query/tool lexical coverage;
- original tool-name coverage;
- small intent-category overlap;
- tiny read/source priors.

Policy filtering happens **before** ranking. A denied tool can never re-enter
through fallback.

The current selector is deliberately simple so that Phase-5 governance can be
audited. A future semantic router can be compared against this deterministic
baseline without changing the execution guard.

The ten-case bilingual benchmark under `benchmarks/omnirag/phase5/` is only an
offline smoke fixture. Its score is not a research-grade result.

---

## 7. Execution guard

`GovernedToolCallSession` wraps the existing RAGFlow ToolCallSession instead of
reimplementing tools.

For every attempted call it enforces:

- tool exists in reviewed registry;
- tool is in the current per-query shortlist;
- policy still permits its risk/hints;
- total call budget;
- per-tool call budget;
- arguments are a JSON object;
- arguments satisfy the tool JSON Schema.

Schema validation errors are replaced with a generic error instead of echoing
the rejected argument value.

### Audit privacy

The OmniRAG governance trace stores:

- tool name;
- source;
- risk;
- success/failure;
- latency;
- argument **keys**;
- ephemeral-key HMAC-SHA256 of the argument object;
- exception type only.

It does not store raw argument values in the OmniRAG trace. The HMAC key is
created per governed session and is not exported.

**Boundary:** RAGFlow's native tool executor currently has its own logging. Phase
5 does not claim to suppress all upstream/native argument logging. Production
logging/redaction policy must therefore be verified separately in the later
runtime deployment.

---

## 8. Stale-tool prevention

RAGFlow's provider-level `bind_tools()` intentionally does nothing when supplied
an empty schema list. Without special handling, a previous invocation's tool
binding could remain visible.

Phase 5 explicitly clears the provider tool list when the policy produces an
empty shortlist. If the feature flag is later turned off on the same Agent
instance, the original full native binding is restored.

Both behaviors have dedicated unit tests.

---

## 9. Reference MCP server

`extensions/omnirag/mcp/reference_server.py` supplies three deterministic,
read-only tools for the later live integration test:

- `lookup_device`;
- `search_runbook`;
- `calculate_availability`.

This server is a **test fixture**, not a new MCP framework. RAGFlow remains the
MCP client and transport owner.

Pure functions are already unit-tested offline. Construction using the external
MCP SDK and a real Streamable HTTP connection are explicitly deferred until the
full project environment is installed.

---

## 10. TaskSpec is an authoring DSL, not a runtime

Phase 5 introduces a deliberately small TaskSpec v1:

```text
retrieval -> agent -> message
```

Allowed step kinds:

- `retrieval`
- `agent`
- `message`

The compiler maps these to RAGFlow's native components:

```text
Retrieval
Agent
Message
```

and emits the existing Canvas-shaped `components`, `graph`, `globals`,
`retrieval`, `memory`, and `variables` structure.

There is no OmniRAG workflow executor.

### Safety restrictions

TaskSpec v1:

- caps the number of steps;
- validates step IDs and dependency DAG;
- rejects unknown top-level and step-level fields;
- validates parameter types and numeric bounds;
- rejects unsupported parameters;
- blocks secret-like parameter fields;
- validates references against direct dependencies;
- validates references against known output names;
- requires every terminal branch to end at a Message;
- does not allow arbitrary code, SQL, HTTP, MCP configuration, or raw tool
  configuration;
- validates before compilation.

Secret handling is stated precisely: Phase 5 blocks secret-like **fields** in
TaskSpec but does not claim generic secret-value detection inside arbitrary
prompt strings.

### Tool/MCP authoring boundary

The compiler intentionally emits:

```json
{"mcp": [], "tools": []}
```

for generated Agent steps. A generated TaskSpec therefore cannot silently
inject a new MCP server or executable tool. Tool provisioning remains a trusted
server/UI configuration concern.

---

## 11. Native Canvas validation boundary

Offline compilation proves that the generated object has the reviewed native
shape. It does **not** prove that every native component constructor/check passes
inside the full service environment.

`phase5_runtime_contract_validate.py` is provided for the later local run. It
will execute RAGFlow's real `Graph.validate_component_parameters()` and construct
the reference FastMCP server after the project runtime dependencies are present.

In the current pre-local environment `quart`, `json_repair`, and `peewee` are not
installed, so that runtime validation is explicitly marked **DEFERRED**, not
PASS.

---

## 12. Integration patch

Phase 5 touches only one RAGFlow core integration owner:

```text
agent/component/agent_with_tools.py
```

The feature-flagged hook calls:

```text
extensions.omnirag.tools.integration.prepare_agent_tools(...)
```

The deliverable tree keeps the original file unchanged. The staged patch is:

```text
patches/omnirag/phase5_tool_governance.patch
```

Required research-patch order:

```text
Phase-1 frozen source
 -> Phase-2 adaptive retrieval
 -> Phase-3 multimodal/verifier
 -> Phase-4 agent governance/memory
 -> Phase-5 tool governance
```

The full ordered stack is applied and syntax-compiled only in an isolated
temporary tree during static validation.

---

## 13. What Phase 5 can and cannot claim before local execution

### Verified offline

- conservative risk/policy contracts;
- contradictory MCP read-only hint cannot downgrade a destructive-looking tool;
- read-only/closed-world defaults;
- deterministic selector contracts;
- shortlist enforcement;
- schema validation;
- tool-call budgets;
- privacy-reduced OmniRAG audit trace;
- TaskSpec parsing/validation/compilation;
- pure reference-server functions;
- all OmniRAG unit tests;
- Phase-2/3/4/5 ordered patch-stack syntax and hashes;
- frozen baseline integrity.

### Not yet claimed

- live MCP connection success;
- native Canvas parameter validation in the complete RAGFlow environment;
- live model tool-choice quality;
- task success improvement;
- production tool latency;
- production security against a malicious remote MCP implementation;
- end-to-end write/execute approval flows;
- semantic tool-router superiority.

Those belong to the later local/integration stage.
