# OmniRAG-Agent Phase 4 — Memory-Aware Agent Governance

## 1. Purpose

Phase 4 adds a conservative control plane around RAGFlow 0.27.2's existing agentic-RAG runtime. It is **not** a replacement planner and it does not claim RAGFlow's built-in planning/reflection capabilities as OmniRAG innovations.

The Phase-4 contribution is:

1. safe long-term strategy-memory recall;
2. a post-generation evidence critic that combines RAGFlow's native sufficient-context verdict with the Phase-3 deterministic verifier;
3. a deterministic bounded retry policy;
4. transparent abstention when evidence remains insufficient/conflicting;
5. fact-free experience-memory consolidation after successful runs;
6. response metadata that makes every governance decision auditable.

All Phase-4 features are disabled by default.

---

## 2. Source-driven correction to the original design

During the source review we verified that RAGFlow already implements a substantial agentic-RAG workflow in `rag/advanced_rag/`:

- question formalization;
- planner/fan-out decomposition;
- native retrieval orchestration;
- a sufficient-context agent;
- missing-evidence analysis;
- query rewriting/follow-up search inside the graph;
- final cited answer composition.

Therefore OmniRAG must not add a second LLM planner that competes with the native one.

A second, more important source finding changed the retry integration design. `dialog_service.rag_agent()` configures:

```python
chat_mdl.mdl.terminal_tools = {"rag"}
```

and the tool loop in `rag/llm/chat_model.py` immediately returns a terminal tool result instead of feeding it back into another outer-model round. Consequently, text appended by `RAGTools.rag()` such as "call rag again" cannot be relied on to produce a deterministic outer retry in this path.

**Correct Phase-4 behavior:** when `OMNIRAG_AGENT_GOVERNANCE=1`, any post-generation critic retry is performed *inside the terminal `rag` tool* before an answer is exposed. The retry is still executed by RAGFlow's native agentic graph; OmniRAG only decides whether another bounded pass is justified and supplies the focus query.

This is more reliable than assuming an outer LLM will see and obey a retry hint.

---

## 3. Architecture

```text
User query
   |
   v
RAGFlow outer agent/router
   |
   +-- optional procedural/episodic planning memory
   |      (strategy only; never citation evidence)
   |
   v
RAGTools.rag  [terminal tool]
   |
   v
RAGFlow native agentic graph
   |-- formalize
   |-- plan/fan-out
   |-- retrieve
   |-- sufficient-context review
   |-- native rewrite/search loops
   `-- cited answer draft
   |
   v
OmniRAG evidence critic
   |-- RAGFlow native _rag_verdict
   `-- Phase-3 deterministic answer/evidence verifier
   |
   +-- ACCEPT ------> expose accepted answer
   |
   +-- RETRIEVE_MORE
   |       |
   |       `--> one bounded focus query --> rerun native graph
   |
   `-- ABSTAIN -----> expose transparent abstention

After ACCEPT only:
   strategy/process summary --> optional RAGFlow long-term memory write
```

---

## 4. Ownership boundaries

### RAGFlow remains responsible for

- search planning;
- query decomposition;
- KB/web retrieval;
- sufficient-context analysis;
- inner graph retries;
- evidence collection;
- final citation composition;
- memory storage implementation.

### OmniRAG Phase 4 is responsible for

- planning-mode policy metadata;
- safe memory selection for strategy context;
- independent post-generation evidence gating;
- a hard post-generation retry budget;
- retry loop guard;
- preventing rejected drafts from leaking into the stream;
- terminal abstention;
- strategy-only memory consolidation.

---

## 5. Evidence critic

The critic uses two independent signal families.

### Gate A — native RAGFlow SCA

Statuses treated as needing more work:

- `UNANSWERABLE`
- `INSUFFICIENT`
- `CONFLICTING`
- `USEFUL_BUT_INCOMPLETE`

### Gate B — OmniRAG Phase-3 verifier

When enabled, Phase 3 reports:

- `pass`
- `retrieve_more`
- `abstain`

along with claim support/conflict information and a confidence score.

### Conservative decision precedence

```text
empty answer
  -> retry if budget remains, else abstain

verifier gap/conflict OR native SCA insufficiency
  -> retry if budget remains, else abstain

all enabled gates pass
  -> accept
```

If both native confidence and verifier confidence exist, the critic uses the minimum for governance metadata. This does not claim probabilistic calibration; it is a conservative aggregation rule.

---

## 6. Bounded retry correctness

`PlanningPolicyV1` supplies the default retry budget by query class. An optional environment override is clamped to `0..3`.

A retry query may be generated only from:

- the original question;
- unsupported claims already identified by the verifier;
- conflicts already identified by the verifier/SCA;
- RAGFlow's own feedback/missing targets.

The reflection code does not invent a missing entity, date, number, or candidate fact.

Every retry is a **fresh native graph run**. `RAGTools.kbinfos` and `_rag_verdict` are reset before the next post-generation pass to avoid undocumented evidence carry-over between graph invocations. The focus query still contains the original task, so the second pass must reconstruct a complete citable answer.

A repeated normalized focus query triggers the loop guard and forces abstention.

---

## 7. Streaming correctness

A post-generation verifier cannot reject an answer that has already been streamed token-by-token to the user. Therefore, when governance is enabled:

- native reasoning/progress can still stream;
- candidate **answer** tokens are buffered;
- the verifier/critic runs after the complete candidate is available;
- only the final accepted answer, or the abstention message, is sent to the answer stream.

When governance is disabled, the original RAGFlow streaming path is preserved by the staged patch.

---

## 8. Long-term memory safety model

Long-term memory is not evidence.

Default planning types:

- `procedural`
- `episodic`

Excluded from planning by default:

- `raw`
- `semantic`

The rendered prompt explicitly tells the router that memories:

- are strategy context only;
- must not be cited;
- must not override retrieved sources.

### No fabricated similarity

RAGFlow's public memory-query result contract returns ranked rows but does not expose the raw hybrid score. OmniRAG therefore does **not** invent a similarity value.

For deterministic pruning it uses:

```text
rank_score       = 1 / log2(source_rank + 1)
lexical_overlap  = transparent token overlap
recency_score    = exponential time decay

final_score =
  0.60 * rank_score
+ 0.25 * lexical_overlap
+ 0.15 * recency_score
```

This score is an OmniRAG selection heuristic, not a claimed RAGFlow search score.

### Tenant isolation

Before recall or write, configured memory IDs are resolved through `MemoryService` and filtered to the current dialog tenant. A request cannot use this extension to cross a tenant boundary merely by supplying another memory ID.

### Write policy

Auto-write is disabled by default. When explicitly enabled:

- writing happens only after final governance action `accept`;
- the record stores strategy/process metadata only;
- the original user query is not copied into the strategy memory envelope;
- the generated answer is not copied into the strategy memory envelope;
- raw-only memory configurations are skipped;
- configurations containing semantic extraction are rejected by default;
- semantic extraction requires a separate explicit opt-in.

This prevents a generated answer from silently becoming a self-reinforcing factual knowledge base.

---

## 9. Native verdict bridge

`merge_critic_into_rag_verdict()` projects the critic result into RAGFlow's established `_rag_verdict` shape so observability and existing status logic remain coherent:

- `retrieve_more` -> `INSUFFICIENT`
- `abstain` -> `UNANSWERABLE` unless native status is already `CONFLICTING`
- `accept` -> native verdict unchanged

Existing missing claims and feedback are retained.

---

## 10. Original-user-question wiring

`RAGTools` already contains `_resolve_effective_question()` and an `original_user_question` constructor argument to prevent outer tool-query compression from dropping part of a multi-hop question. The reviewed `dialog_service.rag_agent()` path did not pass that value.

The Phase-4 integration patch wires:

```python
original_user_question=messages[-1].get("content", "")
```

This activates an existing upstream safeguard rather than creating a competing rewrite method.

---

## 11. Current multimodal boundary

Phase 3 and Phase 4 are intentionally not over-claimed.

- Phase-3 raw-pixel visual sidecar fusion is integrated into the regular `async_chat` RAG path.
- RAGFlow routes a user turn with image attachments and a vision-capable model from `rag_agent` to `async_chat`; Phase-4 agentic governance therefore does not govern that specific upstream branch yet.
- In the native agentic-RAG branch, the Phase-4 critic can reuse the Phase-3 deterministic verifier over the evidence chunks available to `RAGTools`, but this is not the same as raw-pixel visual retrieval inside the agentic graph.

Unifying raw-pixel visual retrieval with the native agentic tool graph is a later integration task; no Phase-4 report should claim it is already complete.

---

## 12. Staged core patch

Phase-4 core integration is intentionally limited to two reviewed owners:

```text
api/db/services/dialog_service.py
rag/advanced_rag/agentic_rag.py
```

The deliverable tree keeps the frozen baseline core untouched. The patch is stored at:

```text
patches/omnirag/phase4_memory_agent_governance.patch
```

Required application order:

```text
Phase 1 frozen source
  -> Phase 2 adaptive retrieval patch
  -> Phase 3 multimodal/verifier patch
  -> Phase 4 memory-agent-governance patch
```

`phase4_apply_patch.py` checks exact pre-Phase-4 SHA-256 hashes before applying.

---

## 13. Offline validation scope

Offline validation proves control-plane properties only. It does **not** prove live model quality.

Validated offline:

- Python syntax;
- deterministic policy tests;
- tenant-memory guards using fakes;
- contract scenarios;
- patch-stack applicability;
- frozen baseline core integrity;
- retry/abstention transitions;
- fact-free strategy-memory behavior.

Not claimed until local runtime:

- retrieval accuracy improvements;
- answer correctness improvement;
- hallucination-rate reduction;
- latency/token costs;
- GPU memory requirements;
- provider-specific tool-call behavior;
- live memory extraction quality.
