# OmniRAG-Agent Phase-1 Deterministic Retrieval Benchmark

This benchmark exists to freeze the untouched RAGFlow 0.27.2 retrieval baseline before any OmniRAG retrieval innovation is introduced.

## Corpus

Six short single-topic documents are intentionally kept below the default chunk budget so document-level relevance is easy to score. The corpus covers exact lexical identifiers, semantic paraphrase, hybrid retrieval, agent memory, MCP, and the future multimodal extension boundary.

## Queries

`queries.jsonl` contains 28 deterministic questions. Each question has exactly one relevant source document. This allows automatic computation of Recall@K, MRR, and NDCG@K.

## Weight sweep

The runtime collector should execute each query with several fixed `vector_similarity_weight` values. Recommended sweep:

- 0.0: term-only **final fusion score**
- 0.3: RAGFlow default-style final hybrid fusion
- 0.5: equal final fusion
- 0.7: vector-heavy final fusion
- 1.0: vector-only **final fusion score**

Important: on the Elasticsearch path, the candidate acquisition stage still includes dense KNN and uses its own fusion behavior. Therefore 0.0 and 1.0 should not be described as pure sparse-only or pure dense-only retrieval systems; this benchmark isolates the user-facing final fusion weight while keeping RAGFlow's candidate generation unchanged.

No core RAGFlow retrieval source must be modified while generating these results.
