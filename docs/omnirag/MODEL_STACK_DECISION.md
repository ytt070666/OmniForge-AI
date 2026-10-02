# OmniRAG-Agent model stack decision

## Frozen first-run stack

The first live run is intentionally conservative. It should prove the RAGFlow baseline before any research feature changes retrieval behavior.

| Role | First-run choice | Serving path | Why |
|---|---|---|---|
| Document engine | Elasticsearch 8.11.3 | RAGFlow Compose | Matches the uploaded baseline and exposes the two-stage retrieval behavior we want to study. |
| Metadata DB | MySQL | RAGFlow Compose | Upstream default and lowest integration risk. |
| Object storage | MinIO | RAGFlow Compose | Upstream default. |
| Cache | Redis | RAGFlow Compose | Upstream default. |
| Queue | NATS | RAGFlow Compose | Matches the current ingestion configuration. |
| Embedding | `Qwen/Qwen3-Embedding-0.6B` | bundled TEI | Already the RAGFlow 0.27.2 Compose default; small enough for reproducible baseline work. |
| Chat/Vision | `Qwen/Qwen3-VL-8B-Instruct` | OpenAI-compatible endpoint, preferably vLLM later | One model covers ordinary chat and later image/document reasoning. |
| Reranker | disabled for Baseline-A; `Qwen/Qwen3-Reranker-0.6B` for Baseline-B | vLLM-compatible rerank endpoint | Separates the effect of the reranker from the retriever and keeps ablations interpretable. |
| DeepDoc | CPU initially | RAGFlow | Avoids mixing parser GPU performance with retrieval experiments. |

## Why we are not starting with the largest models

The project is intended to demonstrate architecture, retrieval research, agent engineering and evaluation. Using a larger model before the retrieval baseline exists increases hardware cost while making debugging slower. Final-quality experiments can later move the embedding/reranker to the 4B profile without changing the interfaces.

## Three prepared profiles

- `cpu_api_first`: lowest-friction first run; remote chat/vision is allowed.
- `research_balanced`: recommended normal research profile; 8B VLM + 0.6B embedding + 0.6B reranker.
- `research_high_quality`: 8B VLM + 4B embedding + 4B reranker for a larger GPU/server.

The exact endpoints and secrets remain environment variables. No API key is committed to source control.
