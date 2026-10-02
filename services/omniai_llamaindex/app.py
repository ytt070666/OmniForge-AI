from __future__ import annotations

import os
from threading import RLock
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from omniai_platform.http_contract import install_http_contract

app = FastAPI(title="OmniAI LlamaIndex Service", version="1.0.0")
install_http_contract(app)
_lock = RLock()
_index = None
_mode = "not_initialized"
_docs: list[dict[str, str]] = []


class Doc(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    text: str = Field(min_length=1)


class IngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    documents: list[Doc]


class QueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1)
    top_k: int = Field(default=4, ge=1, le=50)


def _build_index(items: list[Doc]):
    try:
        from llama_index.core import Document, Settings, VectorStoreIndex
        from llama_index.core.embeddings import MockEmbedding
    except ImportError as exc:
        raise RuntimeError("LlamaIndex is not installed. Install services/omniai_llamaindex/requirements.txt") from exc

    model_name = os.getenv("OMNIAI_LLAMA_EMBED_MODEL", "").strip()
    mode = "mock_embedding_learning"
    if model_name:
        try:
            from llama_index.embeddings.huggingface import HuggingFaceEmbedding
        except ImportError as exc:
            raise RuntimeError("Install llama-index-embeddings-huggingface for OMNIAI_LLAMA_EMBED_MODEL") from exc
        Settings.embed_model = HuggingFaceEmbedding(model_name=model_name)
        mode = f"huggingface:{model_name}"
    else:
        Settings.embed_model = MockEmbedding(embed_dim=64)
    documents = [Document(text=item.text, id_=item.id, metadata={"doc_id": item.id}) for item in items]
    return VectorStoreIndex.from_documents(documents), mode


@app.get("/health")
def health():
    try:
        import llama_index.core  # noqa: F401
        installed = True
    except ImportError:
        installed = False
    return {"ok": True, "service": "omniai-llamaindex", "version": app.version, "framework": "LlamaIndex", "installed": installed, "index_mode": _mode, "documents": len(_docs)}


@app.post("/api/v1/index")
def ingest(payload: IngestRequest):
    global _index, _mode, _docs
    if not payload.documents:
        raise HTTPException(status_code=400, detail="documents must not be empty")
    try:
        index, mode = _build_index(payload.documents)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    with _lock:
        _index = index
        _mode = mode
        _docs = [item.model_dump() for item in payload.documents]
    return {"indexed": len(_docs), "mode": _mode}


@app.post("/api/v1/search")
def search(payload: QueryRequest) -> dict[str, Any]:
    with _lock:
        index = _index
    if index is None:
        raise HTTPException(status_code=409, detail="index has not been built")
    retriever = index.as_retriever(similarity_top_k=payload.top_k)
    rows = retriever.retrieve(payload.query)
    items = []
    for rank, row in enumerate(rows, start=1):
        node = row.node
        items.append({
            "rank": rank,
            "score": float(row.score or 0.0),
            "text": node.get_content(),
            "doc_id": str(node.metadata.get("doc_id") or node.node_id),
        })
    return {"query": payload.query, "items": items, "mode": _mode}
