# Interview Playbook

## 30-second project explanation
OmniRAG-Agent is a governed secondary-development project built on RAGFlow v0.27.2. I intentionally kept RAGFlow's ingestion, Agent Canvas, MCP transport and runtime ownership, then added the parts I wanted to study: adaptive hybrid retrieval, multimodal evidence verification, bounded Agent reflection and memory governance, fail-closed tool selection, a restricted workflow authoring layer, and a LoRA/QLoRA advisory router. The project uses a frozen baseline and ordered hash-checked patches so every later experiment can be compared against the original system.

## Why RAGFlow instead of starting from scratch?
A from-scratch clone would spend most effort recreating ingestion, runtime, UI and MCP infrastructure. The research value is higher if mature infrastructure is reused and the modified algorithms are isolated, testable and attributable.

## What did you personally implement?
Answer only with the modules under `extensions/omnirag`, `scripts/omnirag`, OmniRAG patches, benchmarks, tests and deployment/productization assets. Explicitly identify RAGFlow-owned functionality when discussing upstream behavior.

## Hard questions
### Is your adaptive retrieval proven better?
Not yet in the pre-local package. The ablation harness and protected baseline are ready, but improvement is not claimed until live retrieval artifacts are collected.

### Did you implement MCP?
No. RAGFlow owns MCP protocol integration. I implemented governance around discovered MCP/built-in tools: registry normalization, risk policy, selection, schema/budget checks and audit metadata.

### Is memory used as evidence?
No. Planning memory can influence how the Agent searches or plans, but citations must come from retrieved evidence. This avoids self-reinforcing hallucinations.

### Can the fine-tuned model authorize dangerous tools?
No. The learned router is advisory only. Deterministic fail-closed tool policy remains authoritative.

### What is the biggest unresolved technical risk?
End-to-end behavior under the full runtime: GPU VLM/embedding execution, native MCP runtime contracts, and quantitative interactions among phases. Those are explicitly `not_run` until local/server validation.
