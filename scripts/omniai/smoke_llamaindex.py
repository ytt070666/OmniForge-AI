"""Run a 3-document LlamaIndex index/search HTTP contract in process."""

import json
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient
from llama_index.core.llms import MockLLM
from llama_index.core.schema import TextNode
from services.omniai_llamaindex.app import app


def main() -> None:
    client = TestClient(app)
    health = client.get("/health").json()
    indexed = client.post("/api/v1/index", json={"documents": [
        {"id": "a", "text": "gateway DNS timeout"},
        {"id": "b", "text": "database is healthy"},
        {"id": "c", "text": "GW-01 runbook"},
    ]}).json()
    result = client.post("/api/v1/search", json={"query": "gateway", "top_k": 2}).json()
    assert health["installed"] and indexed["indexed"] == 3
    assert len(result["items"]) == 2 and all(item["doc_id"] for item in result["items"])
    node = TextNode(text="GW-01 incident")
    assert node.get_content() == "GW-01 incident"
    module = importlib.import_module("services.omniai_llamaindex.app")
    response = module._index.as_query_engine(llm=MockLLM(max_tokens=16), similarity_top_k=2).query("gateway")
    assert len(response.source_nodes) == 2
    print(json.dumps({"documents": indexed["indexed"], "retrieved": len(result["items"]), "query_engine_sources": len(response.source_nodes), "mode": result["mode"]}))


if __name__ == "__main__":
    main()
