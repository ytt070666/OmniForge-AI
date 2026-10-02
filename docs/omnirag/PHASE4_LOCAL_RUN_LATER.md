# Phase 4 local runtime sequence — run later

Do not use this sequence until the frozen Phase-1 baseline has been collected.

## 0. Preserve the untouched baseline

Before any patch application, archive the clean project and baseline outputs. The full Phase-4 pre-local package intentionally ships with core files untouched.

## 1. Apply research patches in order

```bash
python scripts/omnirag/phase2_apply_patch.py --apply
python scripts/omnirag/phase3_apply_patch.py --apply
python scripts/omnirag/phase4_apply_patch.py --apply
```

Do not apply Phase 4 directly to the clean `dialog_service.py`: its precondition is the exact Phase-3-applied file.

## 2. Start with governance only

Use a real chat/tool-capable model and the already configured RAGFlow KB, but leave long-term memory writes disabled:

```bash
export OMNIRAG_AGENT_GOVERNANCE=1
export OMNIRAG_EVIDENCE_VERIFIER=1
export OMNIRAG_AGENT_MEMORY=0
export OMNIRAG_AGENT_MEMORY_WRITE=0
```

Collect:

- native `_rag_verdict`;
- OmniRAG verifier decision;
- governance action;
- number of critic-directed passes;
- final citation set;
- end-to-end latency;
- token usage.

## 3. Enable read-only planning memory

Create/configure a tenant-owned RAGFlow memory that includes procedural and/or episodic extraction. Then pass its ID explicitly as `omnirag_memory_ids` in the request or dialog prompt configuration.

```bash
export OMNIRAG_AGENT_MEMORY=1
export OMNIRAG_AGENT_MEMORY_WRITE=0
```

Verify in response metadata:

```text
omnirag_agent.planning_memory_count
```

Manually inspect the router prompt/traces to ensure memories are used as strategy context and are not cited as evidence.

## 4. Enable strategy write only after read-only validation

```bash
export OMNIRAG_AGENT_MEMORY_WRITE=1
export OMNIRAG_AGENT_ALLOW_SEMANTIC_MEMORY_WRITE=0
```

Check that:

- failed/abstained runs do not write;
- accepted runs write a strategy/process record;
- the raw envelope does not contain the original user question or final answer;
- a memory configured with semantic extraction is skipped by default;
- cross-tenant memory IDs are ignored.

## 5. Runtime ablation matrix

Run the same evaluation set with fixed model/KBase/index state:

| Run | Native Agentic RAG | Phase-3 verifier | Phase-4 governance | Planning memory | Memory write |
|---|---:|---:|---:|---:|---:|
| A | on | off | off | off | off |
| B | on | on | off | off | off |
| C | on | on | on | off | off |
| D | on | on | on | on | off |
| E | on | on | on | on | on |

Never compare runs if the KB/index/model version changed between them.

## 6. Metrics to collect live

Agent/evidence:

- Task Success Rate
- Citation Precision/Recall
- Faithfulness / supported-claim ratio
- Abstention precision on deliberately unanswerable questions
- Critic retry rate
- Retry recovery rate
- Native SCA vs OmniRAG critic disagreement rate

Efficiency:

- total latency
- time to first visible progress
- number of native graph runs
- prompt/completion tokens
- average retrieved chunks

Memory:

- planning-memory hit rate
- useful-memory rate (manual or held-out evaluator)
- memory-induced regression rate
- duplicate strategy-memory rate

Do not publish any metric before the local run actually produces it.

## 7. Streaming-specific check

With governance enabled, verify on the network/SSE stream that a rejected first draft is never emitted as answer text. Reasoning/progress may be visible; only the accepted final answer or transparent abstention should appear in the answer channel.

## 8. Multimodal boundary check

Test regular Phase-3 multimodal RAG separately from Phase-4 agentic RAG. Do not report the two as one unified raw-pixel agentic pipeline until the future tool-graph integration is implemented and measured.
