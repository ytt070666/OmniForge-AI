# OmniRAG Phase-3 Multimodal Benchmark

This benchmark is intentionally synthetic and deterministic. It exists to test
whether the visual retrieval path works before moving to public multimodal RAG
benchmarks and real enterprise documents.

- 6 PNG assets: topology, bar chart, line chart, table, security dashboard, workflow diagram.
- 18 questions: explicit visual, cross-lingual visual and multi-image evidence questions.
- The paired text descriptions deliberately omit several exact facts that are visible in the images.

`HashEncoderForTests` is valid only for plumbing tests. Do **not** report its
retrieval scores as model quality. Real metrics require the configured joint
text-image encoder (Phase-3 default: SigLIP2) and, later, public benchmark data.
