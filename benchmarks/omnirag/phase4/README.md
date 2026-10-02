# OmniRAG Phase 4 contract scenarios

These scenarios are **deterministic contract checks**, not model-quality benchmarks. They validate the control-plane rules that must hold before any live LLM/GPU experiment:

- an answer is accepted only after the configured evidence gates pass;
- verifier or native RAGFlow sufficiency gaps trigger only bounded retries;
- exhausted/conflicting runs abstain;
- long-term planning memory excludes RAW and SEMANTIC facts by default;
- memory relevance uses returned rank explicitly rather than inventing a raw similarity score;
- critic decisions are projected into RAGFlow's native verdict contract;
- strategy memory is written only after an accepted run.

No accuracy, latency, token, or hallucination-rate claim should be inferred from this file. Those metrics are collected only during the later local runtime evaluation.
