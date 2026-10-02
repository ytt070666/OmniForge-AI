#!/usr/bin/env python3
"""Upload and parse the six protected Phase-3 images in a dedicated RAGFlow dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.omnirag.phase1_collect_baseline import RagflowClient

ASSETS = ROOT / "benchmarks" / "omnirag" / "phase3" / "assets"


def save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--auth-file", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--api-root", default="http://127.0.0.1:9380/api/v1")
    parser.add_argument("--parse", action="store_true")
    parser.add_argument("--timeout", type=int, default=1200)
    args = parser.parse_args()
    auth = json.loads(args.auth_file.read_text(encoding="utf-8-sig"))
    client = RagflowClient(args.api_root, auth["api_key"], timeout=120)
    assets = sorted(ASSETS.glob("*.png"))
    if len(assets) != 6:
        raise RuntimeError(f"expected six fixed PNG assets, found {len(assets)}")
    hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in assets}

    if args.manifest.exists():
        state = json.loads(args.manifest.read_text(encoding="utf-8"))
        if state.get("source_sha256") != hashes:
            raise RuntimeError("source image hashes changed since the dataset was created")
    else:
        name = f"omniai-phase3-images-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}"
        dataset = client.post("datasets", json={"name": name, "chunk_method": "picture"})["data"]
        state = {"dataset_id": dataset["id"], "dataset_name": name, "source_sha256": hashes, "documents": []}
        save(args.manifest, state)
        with ExitStack() as stack:
            files = [("file", (path.name, stack.enter_context(path.open("rb")), "image/png")) for path in assets]
            docs = client.post(f"datasets/{dataset['id']}/documents", files=files, timeout=180)["data"]
        if len(docs) != len(assets):
            raise RuntimeError(f"uploaded {len(docs)} of {len(assets)} images")
        state["documents"] = [{"id": doc["id"], "name": doc["name"], "run": doc.get("run")} for doc in docs]
        save(args.manifest, state)
        print(f"uploaded {len(docs)} images to dataset {dataset['id']}", flush=True)

    if not args.parse:
        return 0
    ids = [doc["id"] for doc in state["documents"]]
    if len(ids) != 6:
        raise RuntimeError("manifest has no complete document list; inspect before retrying")
    list_path = f"datasets/{state['dataset_id']}/documents"
    try:
        current = client.get(list_path, params={"page": 1, "page_size": 100})["data"]
        current_docs = {doc["id"]: doc for doc in current.get("docs", []) if doc["id"] in ids}
        if len(current_docs) == 6 and all(current_docs[doc_id].get("run") == "DONE" for doc_id in ids):
            state["documents"] = [
                {"id": doc_id, "name": current_docs[doc_id]["name"], "run": "DONE",
                 "chunk_count": current_docs[doc_id].get("chunk_count")}
                for doc_id in ids
            ]
            save(args.manifest, state)
            print("all six image documents are already DONE", flush=True)
            return 0
    except requests.RequestException:
        pass
    client.post(f"datasets/{state['dataset_id']}/documents/parse", json={"document_ids": ids})
    deadline = time.monotonic() + args.timeout
    while time.monotonic() < deadline:
        try:
            data = client.get(list_path, params={"page": 1, "page_size": 100})["data"]
        except requests.RequestException as exc:
            print(f"transient document-list error: {type(exc).__name__}", flush=True)
            time.sleep(5)
            continue
        docs = {doc["id"]: doc for doc in data.get("docs", []) if doc["id"] in ids}
        state["documents"] = [
            {"id": doc_id, "name": docs[doc_id]["name"], "run": docs[doc_id].get("run"),
             "chunk_count": docs[doc_id].get("chunk_count"), "progress_msg": docs[doc_id].get("progress_msg")}
            for doc_id in ids if doc_id in docs
        ]
        save(args.manifest, state)
        runs = [doc.get("run") for doc in state["documents"]]
        print(f"parse states: {runs}", flush=True)
        if len(runs) == 6 and all(run == "DONE" for run in runs):
            return 0
        if any(run in {"FAIL", "FAILED", "CANCEL"} for run in runs):
            raise RuntimeError("an image parse failed; inspect the manifest and RAGFlow logs")
        time.sleep(5)
    raise TimeoutError(f"image parse did not finish within {args.timeout}s")


if __name__ == "__main__":
    raise SystemExit(main())
