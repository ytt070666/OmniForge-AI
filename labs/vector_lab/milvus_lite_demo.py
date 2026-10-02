from __future__ import annotations

from pathlib import Path


def main() -> None:
    try:
        from pymilvus import MilvusClient
    except ImportError as exc:
        raise SystemExit("Install pymilvus[milvus-lite] before running this lab") from exc
    db = Path("artifacts/omniai/vector_lab/milvus.db")
    db.parent.mkdir(parents=True, exist_ok=True)
    client = MilvusClient(str(db))
    name = "learning_vectors"
    if client.has_collection(name):
        client.drop_collection(name)
    client.create_collection(collection_name=name, dimension=4)
    try:
        client.insert(name, [
            {"id": 1, "vector": [1.0, 0.0, 0.0, 0.0], "text": "gateway"},
            {"id": 2, "vector": [0.0, 1.0, 0.0, 0.0], "text": "database"},
        ])
        print(client.search(name, data=[[0.9, 0.1, 0.0, 0.0]], limit=2, output_fields=["text"]))
    finally:
        client.drop_collection(name)
    assert not client.has_collection(name), "test collection was not removed"


if __name__ == "__main__":
    main()
