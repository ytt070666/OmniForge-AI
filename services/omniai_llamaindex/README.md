# OmniAI LlamaIndex Service

This isolated service exists so LlamaIndex can be learned and compared without
replacing RAGFlow/OmniRAG. It exposes a small `index -> retrieve` REST contract.
The default mock embedding mode is only for framework plumbing; set
`OMNIAI_LLAMA_EMBED_MODEL` and install the Hugging Face integration before
claiming semantic retrieval quality.
