# Phase 5 offline fixtures

These fixtures validate **contracts**, not model quality.

## `tool_selection_cases.jsonl`

Ten synthetic bilingual queries over a five-tool capability catalog. The offline
selector script reports Top-1/Top-3 shortlist routing. This dataset is tiny and
hand-constructed; a perfect score is only a smoke-test result and **must not be
reported as an end-to-end Agent/tool-use metric**.

The later live experiment must use a larger held-out task set and measure at
least:

- tool selection accuracy;
- tool execution success;
- task success rate;
- policy-denial correctness;
- unnecessary-tool rate;
- latency/token overhead;
- unsafe write/execute invocation rate.

## `taskspec_grounded_qa.json`

A restricted TaskSpec-v1 authoring example:

`Retrieval -> Agent -> Message`

It contains placeholder dataset/model IDs. Compilation proves only that the
restricted schema maps deterministically to the reviewed RAGFlow Canvas-shaped
DSL. Native component validation and actual Canvas execution are deferred until
the full RAGFlow runtime is installed.
