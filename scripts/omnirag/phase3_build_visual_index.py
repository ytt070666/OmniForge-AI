#!/usr/bin/env python3
"""Build the OmniRAG Phase-3 visual sidecar index.

Modes:
- benchmark: encode the checked-in synthetic benchmark images;
- ragflow: enumerate parsed RAGFlow chunks, download chunk images through the
  public REST API, and encode them into the same joint text-image space.

The default encoder is SigLIP2. ``--encoder hash`` exists only to validate the
plumbing offline and must never be used for reported research metrics.
"""

from __future__ import annotations

import argparse
import sys
import json
import os
import tempfile
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
BENCH = ROOT / "benchmarks" / "omnirag" / "phase3"
DEFAULT_INDEX = ROOT / "artifacts" / "omnirag" / "visual_index.jsonl"

from extensions.omnirag.multimodal.types import VisualRecord
from extensions.omnirag.multimodal.visual_encoder import HashEncoderForTests, Siglip2Encoder
from extensions.omnirag.multimodal.visual_index import JsonlVisualIndex


class Client:
    def __init__(self, api_root: str, api_key: str):
        self.root = api_root.rstrip("/")
        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Bearer {api_key}"})

    def json(self, method: str, path: str, **kwargs):
        r = self.s.request(method, f"{self.root}/{path.lstrip('/')}", timeout=120, **kwargs)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict) and data.get("code") not in (None, 0):
            raise RuntimeError(data)
        return data.get("data") if isinstance(data, dict) else data

    def image(self, image_id: str) -> bytes:
        r = self.s.get(f"{self.root}/documents/images/{quote(image_id, safe='')}", timeout=120)
        r.raise_for_status()
        return r.content


def load_encoder(name: str):
    if name == "hash":
        print("WARNING: hash encoder is plumbing-only and invalid for research metrics")
        return HashEncoderForTests()
    if name == "siglip2":
        return Siglip2Encoder()
    raise SystemExit(f"Unknown encoder: {name}")


def benchmark_records(encoder) -> list[VisualRecord]:
    rows = [json.loads(x) for x in (BENCH / "visual_records.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    paths = [str(BENCH / "assets" / row["asset"]) for row in rows]
    vectors = encoder.encode_images(paths)
    out = []
    for row, vec in zip(rows, vectors):
        out.append(VisualRecord(
            chunk_id=row["chunk_id"], dataset_id=row["dataset_id"], document_id=row["document_id"],
            document_name=row["document_name"], image_id=row["image_id"], content=row["content"],
            vector=tuple(vec), doc_type=row.get("doc_type", "image"), metadata=row.get("metadata", {}),
        ))
    return out


def ragflow_records(client: Client, dataset_ids: list[str], encoder) -> list[VisualRecord]:
    pending: list[tuple[dict, Path]] = []
    tempdir = tempfile.TemporaryDirectory(prefix="omnirag-visual-")
    tmp = Path(tempdir.name)
    try:
        for dataset_id in dataset_ids:
            page = 1
            while True:
                data = client.json("GET", f"datasets/{dataset_id}/documents", params={"page": page, "page_size": 100}) or {}
                docs = data.get("docs") or []
                for doc in docs:
                    doc_id = doc["id"]
                    cpage = 1
                    while True:
                        chunk_data = client.json("GET", f"datasets/{dataset_id}/documents/{doc_id}/chunks", params={"page": cpage, "page_size": 100}) or {}
                        chunks = chunk_data.get("chunks") or []
                        for chunk in chunks:
                            image_id = chunk.get("image_id") or ""
                            if not image_id:
                                continue
                            raw = client.image(image_id)
                            ext = ".png" if raw[:8] == b"\x89PNG\r\n\x1a\n" else ".jpg"
                            local = tmp / f"{chunk['id']}{ext}"
                            local.write_bytes(raw)
                            pending.append(({
                                "chunk_id": chunk["id"], "dataset_id": dataset_id, "document_id": doc_id,
                                "document_name": doc.get("name") or chunk.get("docnm_kwd") or "",
                                "image_id": image_id, "content": chunk.get("content") or "",
                                "doc_type": chunk.get("doc_type_kwd") or "image",
                                "metadata": {"positions": chunk.get("positions") or []},
                            }, local))
                        if len(chunks) < 100:
                            break
                        cpage += 1
                if len(docs) < 100:
                    break
                page += 1
        vectors = encoder.encode_images([str(p) for _, p in pending])
        return [VisualRecord(vector=tuple(vec), **meta) for (meta, _), vec in zip(pending, vectors)]
    finally:
        tempdir.cleanup()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", choices=["benchmark", "ragflow"], default="benchmark")
    ap.add_argument("--encoder", choices=["siglip2", "hash"], default=os.getenv("OMNIRAG_VISUAL_ENCODER", "siglip2"))
    ap.add_argument("--output", type=Path, default=DEFAULT_INDEX)
    ap.add_argument("--api-root", default=os.getenv("RAGFLOW_API_ROOT", "http://127.0.0.1:9380/api/v1"))
    ap.add_argument("--api-key", default=os.getenv("RAGFLOW_API_KEY"))
    ap.add_argument("--dataset-id", action="append", default=[])
    args = ap.parse_args()
    encoder = load_encoder(args.encoder)
    if args.source == "benchmark":
        records = benchmark_records(encoder)
    else:
        if not args.api_key or not args.dataset_id:
            raise SystemExit("ragflow source requires --api-key/RAGFLOW_API_KEY and at least one --dataset-id")
        records = ragflow_records(Client(args.api_root, args.api_key), args.dataset_id, encoder)
    JsonlVisualIndex(args.output).replace(records)
    print(f"Wrote {len(records)} records -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
