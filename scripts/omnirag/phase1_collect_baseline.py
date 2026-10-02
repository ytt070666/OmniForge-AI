#!/usr/bin/env python3
"""Collect an untouched RAGFlow retrieval baseline for OmniRAG-Agent Phase 1.

This script intentionally uses only public REST endpoints. It does not import or
modify RAGFlow retrieval internals, so results remain suitable as a baseline for
later algorithmic changes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "benchmarks" / "omnirag" / "phase1"
CORPUS = BENCH / "corpus"
QUERIES = BENCH / "queries.jsonl"
DEFAULT_WEIGHTS = [0.0, 0.3, 0.5, 0.7, 1.0]


class ApiError(RuntimeError):
    pass


class RagflowClient:
    def __init__(self, api_root: str, token: str, timeout: int = 60):
        self.api_root = api_root.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        url = f"{self.api_root}/{path.lstrip('/')}"
        timeout = kwargs.pop("timeout", self.timeout)
        started = time.perf_counter()
        response = self.session.request(method, url, timeout=timeout, **kwargs)
        elapsed_ms = (time.perf_counter() - started) * 1000
        try:
            payload = response.json()
        except ValueError as exc:
            if path.lstrip('/') == 'system/ping' and response.status_code == 200 and response.text.strip() == 'pong':
                return {'code': 0, 'data': 'pong', '_client_elapsed_ms': elapsed_ms}
            raise ApiError(f"{method} {url} returned non-JSON HTTP {response.status_code}: {response.text[:500]}") from exc
        if response.status_code >= 400:
            raise ApiError(f"{method} {url} failed HTTP {response.status_code}: {payload}")
        if not isinstance(payload, dict):
            raise ApiError(f"{method} {url} returned unexpected payload: {payload!r}")
        if payload.get("code") not in (None, 0):
            raise ApiError(f"{method} {url} failed: {payload}")
        payload["_client_elapsed_ms"] = elapsed_ms
        return payload

    def get(self, path: str, **kwargs: Any) -> dict[str, Any]:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> dict[str, Any]:
        return self.request("POST", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> dict[str, Any]:
        return self.request("DELETE", path, **kwargs)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_queries(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid JSON in {path}:{line_no}: {exc}") from exc
        required = {"id", "category", "question", "expected_document"}
        missing = required - set(row)
        if missing:
            raise SystemExit(f"Missing {sorted(missing)} in {path}:{line_no}")
        rows.append(row)
    return rows


def ping(client: RagflowClient) -> dict[str, Any]:
    info: dict[str, Any] = {}
    for endpoint in ("system/ping", "system/version", "system/status"):
        try:
            info[endpoint] = client.get(endpoint, timeout=20)
        except Exception as exc:  # status availability differs by deployment mode
            info[endpoint] = {"error": str(exc)}
    if isinstance(info.get("system/ping"), dict) and info["system/ping"].get("error"):
        raise ApiError(f"RAGFlow ping failed: {info['system/ping']['error']}")
    return info


def create_dataset(client: RagflowClient, name: str) -> dict[str, Any]:
    payload = client.post("datasets", json={"name": name})
    data = payload.get("data") or {}
    if not data.get("id"):
        raise ApiError(f"Dataset create response has no id: {payload}")
    return data


def upload_corpus(client: RagflowClient, dataset_id: str) -> list[dict[str, Any]]:
    files = sorted(p for p in CORPUS.iterdir() if p.is_file())
    if not files:
        raise SystemExit(f"No corpus files found under {CORPUS}")
    with ExitStack() as stack:
        multipart = []
        for path in files:
            handle = stack.enter_context(path.open("rb"))
            multipart.append(("file", (path.name, handle, "text/plain")))
        payload = client.post(f"datasets/{dataset_id}/documents", files=multipart, timeout=180)
    data = payload.get("data") or []
    if len(data) != len(files):
        raise ApiError(f"Expected {len(files)} uploaded documents, got {len(data)}: {payload}")
    return data


def start_parse(client: RagflowClient, dataset_id: str, document_ids: list[str]) -> None:
    client.post(
        f"datasets/{dataset_id}/documents/parse",
        json={"document_ids": document_ids},
        timeout=120,
    )


def wait_for_parse(client: RagflowClient, dataset_id: str, document_ids: list[str], timeout_s: int) -> list[dict[str, Any]]:
    deadline = time.time() + timeout_s
    wanted = set(document_ids)
    latest: list[dict[str, Any]] = []
    while time.time() < deadline:
        payload = client.get(
            f"datasets/{dataset_id}/documents",
            params={"page": 1, "page_size": max(100, len(document_ids))},
            timeout=30,
        )
        data = payload.get("data") or {}
        docs = data.get("docs") or []
        latest = [d for d in docs if d.get("id") in wanted]
        states = {str(d.get("run")) for d in latest}
        if len(latest) == len(wanted) and states == {"DONE"}:
            return latest
        bad = [d for d in latest if str(d.get("run")) in {"FAIL", "FAILED", "CANCEL"}]
        if bad:
            raise ApiError(f"Document parsing failed: {bad}")
        print(f"[wait] parsing states={sorted(states)} docs={len(latest)}/{len(wanted)}", flush=True)
        time.sleep(2)
    raise TimeoutError(f"Document parsing did not reach DONE within {timeout_s}s. Latest={latest}")


def compact_chunk(chunk: dict[str, Any], rank: int) -> dict[str, Any]:
    content = str(chunk.get("content") or chunk.get("content_with_weight") or "")
    return {
        "rank": rank,
        "id": chunk.get("id") or chunk.get("chunk_id"),
        "document_id": chunk.get("document_id") or chunk.get("doc_id"),
        "document_keyword": chunk.get("document_keyword") or chunk.get("docnm_kwd"),
        "dataset_id": chunk.get("dataset_id") or chunk.get("kb_id"),
        "similarity": chunk.get("similarity"),
        "vector_similarity": chunk.get("vector_similarity"),
        "term_similarity": chunk.get("term_similarity"),
        "important_keywords": chunk.get("important_keywords") or chunk.get("important_kwd"),
        "content": content[:2000],
    }


def collect_retrieval(
    client: RagflowClient,
    dataset_id: str,
    queries: list[dict[str, Any]],
    weights: list[float],
    output: Path,
    page_size: int,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as sink:
        total = len(queries) * len(weights)
        seq = 0
        for weight in weights:
            for query in queries:
                seq += 1
                body = {
                    "dataset_ids": [dataset_id],
                    "question": query["question"],
                    "page": 1,
                    "page_size": page_size,
                    "similarity_threshold": 0.0,
                    "vector_similarity_weight": weight,
                    "knn_top_k": 128,
                    "knn_num_candidates": 256,
                    "rerank_candidates_count": 64,
                    "highlight": False,
                    "include_knowledge_compilation": False,
                }
                started = time.perf_counter()
                payload = client.post("retrieval", json=body, timeout=120)
                elapsed_ms = (time.perf_counter() - started) * 1000
                data = payload.get("data") or {}
                chunks = [compact_chunk(c, i + 1) for i, c in enumerate(data.get("chunks") or [])]
                row = {
                    "query_id": query["id"],
                    "category": query["category"],
                    "question": query["question"],
                    "expected_document": query["expected_document"],
                    "expected_markers": query.get("expected_markers", []),
                    "vector_similarity_weight": weight,
                    "term_similarity_weight": 1.0 - weight,
                    "latency_ms": round(elapsed_ms, 3),
                    "retrieved_total": data.get("total", 0),
                    "chunks": chunks,
                }
                sink.write(json.dumps(row, ensure_ascii=False) + "\n")
                sink.flush()
                print(f"[{seq:03d}/{total:03d}] weight={weight:.1f} {query['id']} chunks={len(chunks)} {elapsed_ms:.1f}ms", flush=True)


def create_chat(client: RagflowClient, dataset_id: str, name: str, weight: float) -> str:
    payload = client.post(
        "chats",
        json={
            "name": name,
            "dataset_ids": [dataset_id],
            "top_n": 6,
            "rerank_candidates_count": 64,
            "top_k": 128,
            "similarity_threshold": 0.0,
            "vector_similarity_weight": weight,
        },
        timeout=60,
    )
    data = payload.get("data") or {}
    if not data.get("id"):
        raise ApiError(f"Chat create response has no id: {payload}")
    return data["id"]


def collect_chat(
    client: RagflowClient,
    dataset_id: str,
    queries: list[dict[str, Any]],
    output: Path,
    limit: int,
    weight: float,
) -> dict[str, Any]:
    chat_name = f"OmniRAG_Phase1_Chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    chat_id = create_chat(client, dataset_id, chat_name, weight)
    selected = queries if limit <= 0 else queries[:limit]
    with output.open("w", encoding="utf-8") as sink:
        for idx, query in enumerate(selected, start=1):
            started = time.perf_counter()
            payload = client.post(
                "chat/completions",
                json={
                    "chat_id": chat_id,
                    "messages": [{"role": "user", "content": query["question"]}],
                    "stream": False,
                    "pass_all_history_messages": True,
                    "store_history_messages": False,
                },
                timeout=180,
            )
            elapsed_ms = (time.perf_counter() - started) * 1000
            data = payload.get("data") or {}
            row = {
                "query_id": query["id"],
                "question": query["question"],
                "expected_document": query["expected_document"],
                "latency_ms": round(elapsed_ms, 3),
                "answer": data.get("answer"),
                "reference": data.get("reference"),
                "chat_id": chat_id,
            }
            sink.write(json.dumps(row, ensure_ascii=False) + "\n")
            sink.flush()
            print(f"[chat {idx:03d}/{len(selected):03d}] {query['id']} {elapsed_ms:.1f}ms", flush=True)
    return {"chat_id": chat_id, "chat_name": chat_name, "count": len(selected)}


def parse_weights(raw: str) -> list[float]:
    out = []
    for part in raw.split(","):
        value = float(part.strip())
        if value < 0 or value > 1:
            raise argparse.ArgumentTypeError("weights must be between 0 and 1")
        out.append(value)
    return out


def build_manifest(
    dataset: dict[str, Any],
    uploaded: list[dict[str, Any]],
    parsed: list[dict[str, Any]],
    system_info: dict[str, Any],
    weights: list[float],
) -> dict[str, Any]:
    corpus_files = sorted(p for p in CORPUS.iterdir() if p.is_file())
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "baseline": {
            "project": "RAGFlow",
            "version": "0.27.2",
            "archive_commit": "a024bea0cd93f39e6652a42bf84dd20c55bc560b",
            "algorithm_modified": False,
        },
        "dataset": dataset,
        "documents_uploaded": uploaded,
        "documents_parsed": parsed,
        "corpus_sha256": {p.name: sha256(p) for p in corpus_files},
        "queries_sha256": sha256(QUERIES),
        "weights": weights,
        "system": system_info,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-root", default=os.getenv("RAGFLOW_API_ROOT", "http://127.0.0.1:9380/api/v1"))
    parser.add_argument("--api-key", default=os.getenv("RAGFLOW_API_KEY"))
    parser.add_argument("--weights", type=parse_weights, default=DEFAULT_WEIGHTS, help="comma-separated vector weights, default 0,0.3,0.5,0.7,1")
    parser.add_argument("--page-size", type=int, default=10)
    parser.add_argument("--parse-timeout", type=int, default=900)
    parser.add_argument("--results-dir", type=Path, default=BENCH / "results")
    parser.add_argument("--include-chat", action="store_true", help="also collect generation output; requires a configured default chat model")
    parser.add_argument("--chat-limit", type=int, default=6, help="number of queries for generation; 0 means all")
    parser.add_argument("--chat-weight", type=float, default=0.3)
    parser.add_argument("--cleanup", action="store_true", help="delete the generated dataset after collection")
    parser.add_argument("--dry-run", action="store_true", help="validate local benchmark files without contacting RAGFlow")
    args = parser.parse_args()

    queries = load_queries(QUERIES)
    if args.page_size < 5 or args.page_size > 64:
        parser.error("--page-size should be between 5 and 64 for this benchmark")
    if args.chat_weight < 0 or args.chat_weight > 1:
        parser.error("--chat-weight must be between 0 and 1")

    corpus_files = sorted(p.name for p in CORPUS.iterdir() if p.is_file())
    if args.dry_run:
        print(json.dumps({"corpus_files": corpus_files, "query_count": len(queries), "weights": args.weights}, indent=2, ensure_ascii=False))
        return 0

    if not args.api_key:
        parser.error("RAGFLOW_API_KEY is required. Create/copy a RAGFlow HTTP API key and export it before running.")

    client = RagflowClient(args.api_root, args.api_key)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = args.results_dir / run_id
    results_dir.mkdir(parents=True, exist_ok=True)
    dataset_name = f"OmniRAG_Phase1_Baseline_{run_id}"
    dataset_id: str | None = None

    try:
        print("[1/7] Checking RAGFlow API...")
        system_info = ping(client)

        print(f"[2/7] Creating dataset {dataset_name}...")
        dataset = create_dataset(client, dataset_name)
        dataset_id = dataset["id"]

        print(f"[3/7] Uploading {len(corpus_files)} corpus documents...")
        uploaded = upload_corpus(client, dataset_id)
        document_ids = [d["id"] for d in uploaded]

        print("[4/7] Starting document parsing...")
        start_parse(client, dataset_id, document_ids)
        parsed = wait_for_parse(client, dataset_id, document_ids, args.parse_timeout)

        print(f"[5/7] Collecting retrieval weight sweep for {len(queries)} queries...")
        retrieval_file = results_dir / "retrieval_results.jsonl"
        collect_retrieval(client, dataset_id, queries, args.weights, retrieval_file, args.page_size)

        chat_meta = None
        if args.include_chat:
            print("[6/7] Collecting chat completion samples...")
            chat_file = results_dir / "chat_results.jsonl"
            chat_meta = collect_chat(client, dataset_id, queries, chat_file, args.chat_limit, args.chat_weight)
        else:
            print("[6/7] Chat collection skipped. Add --include-chat after configuring a default chat model.")

        print("[7/7] Writing run manifest...")
        manifest = build_manifest(dataset, uploaded, parsed, system_info, args.weights)
        manifest["retrieval_results"] = str(retrieval_file.relative_to(ROOT))
        manifest["chat"] = chat_meta
        (results_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        (BENCH / "results" / "LATEST").write_text(run_id + "\n", encoding="utf-8")

        print(f"\nPASS: baseline collected under {results_dir}")
        print("Next: python3 scripts/omnirag/phase1_evaluate_baseline.py --results-dir " + str(results_dir))
        return 0
    except Exception as exc:
        print(f"\nFAIL: {exc}", file=sys.stderr)
        return 1
    finally:
        if args.cleanup and dataset_id:
            try:
                client.delete("datasets", json={"ids": [dataset_id]}, timeout=120)
                print(f"[cleanup] deleted dataset {dataset_id}")
            except Exception as exc:
                print(f"[cleanup warning] failed to delete dataset: {exc}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
