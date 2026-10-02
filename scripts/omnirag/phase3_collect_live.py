#!/usr/bin/env python3
"""Run the 18 protected Phase-3 questions through live RAGFlow chat and persist evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.omnirag.phase1_collect_baseline import RagflowClient, create_chat

BENCH = ROOT / "benchmarks" / "omnirag" / "phase3"
DIALOG_SERVICE = ROOT / "api" / "db" / "services" / "dialog_service.py"


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def find_metadata(reference: dict, key: str) -> dict:
    if key in reference:
        return reference[key] or {}
    return {}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--auth-file", type=Path, required=True)
    parser.add_argument("--ingest-manifest", type=Path, required=True)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=18)
    parser.add_argument("--top-n", type=int, default=6, help="chat retrieval limit; default preserves the original six chunks")
    parser.add_argument("--llm-id", default="", help="optional API override; the local Ollama instance uses the tenant default")
    parser.add_argument("--expected-model", default="omniai-vl-2b:8k@omniai-gate3-vl-8k-local@Ollama")
    parser.add_argument("--api-root", default="http://127.0.0.1:9380/api/v1")
    parser.add_argument("--prompt-config", type=Path, help="optional chat prompt config JSON for a separate ablation")
    parser.add_argument("--verifier-source", type=Path, help="verifier source mounted by an experimental Compose overlay")
    parser.add_argument("--query-id", action="append", help="run only a protected query ID; repeat for a pilot")
    args = parser.parse_args()
    if not 1 <= args.top_n <= 6:
        parser.error("--top-n must be between 1 and 6")
    prompt_config = json.loads(args.prompt_config.read_text(encoding="utf-8")) if args.prompt_config else None
    auth = json.loads(args.auth_file.read_text(encoding="utf-8-sig"))
    ingest = json.loads(args.ingest_manifest.read_text(encoding="utf-8"))
    fixed_queries = rows(BENCH / "queries.jsonl")
    if len(fixed_queries) != 18:
        raise RuntimeError("protected Phase-3 query count changed")
    selected_ids = set(args.query_id or [])
    if selected_ids - {query["id"] for query in fixed_queries}:
        raise RuntimeError(f"unknown query IDs: {sorted(selected_ids - {query['id'] for query in fixed_queries})}")
    benchmark_images = {row["chunk_id"]: row["document_name"] for row in rows(BENCH / "visual_records.jsonl")}
    index = {row["document_name"]: row for row in rows(args.index)}
    if len(index) != 6:
        raise RuntimeError("real RAGFlow index must contain six image rows")
    for query in fixed_queries:
        names = [benchmark_images[item] for item in query.get("expected_chunks", [query.get("expected_chunk")])]
        if any(name not in index for name in names):
            raise RuntimeError(f"missing real image for {query['id']}")

    args.results_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.results_dir / "run_manifest.json"
    result_path = args.results_dir / "live_results.jsonl"
    client = RagflowClient(args.api_root, auth["api_key"], timeout=300)
    default_model = client.get("users/me/models")["data"].get("llm_id")
    if not args.llm_id and default_model != args.expected_model:
        raise RuntimeError(f"tenant default chat model changed: {default_model}")
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (manifest["queries_sha256"] != digest(BENCH / "queries.jsonl")
            or manifest["index_sha256"] != digest(args.index)
            or manifest["llm_id"] != (args.llm_id or default_model)
            or manifest.get("top_n", 6) != args.top_n
            or manifest.get("prompt_config_sha256") != (digest(args.prompt_config) if args.prompt_config else None)
            or manifest.get("verifier_sha256") != (digest(args.verifier_source) if args.verifier_source else None)
            or (manifest.get("dialog_service_sha256") and manifest["dialog_service_sha256"] != digest(DIALOG_SERVICE))):
            raise RuntimeError("query, index, model, top_n, prompt config, verifier, or service hash changed after run creation")
        chat_id = manifest["chat_id"]
    else:
        chat_name = f"OmniRAG_Phase3_Live_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}"
        if prompt_config is None and args.top_n == 6:
            chat_id = create_chat(client, ingest["dataset_id"], chat_name, 0.3)
        else:
            payload = client.post("chats", json={
                "name": chat_name, "dataset_ids": [ingest["dataset_id"]],
                "top_n": args.top_n, "rerank_candidates_count": 64, "top_k": 128,
                "similarity_threshold": 0.0, "vector_similarity_weight": 0.3,
                **({"prompt_config": prompt_config} if prompt_config is not None else {}),
            }, timeout=60)
            chat_id = (payload.get("data") or {}).get("id")
            if not chat_id:
                raise RuntimeError(f"chat create response has no id: {payload}")
        manifest = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "dataset_id": ingest["dataset_id"],
            "chat_id": chat_id,
            "chat_name": chat_name,
            "queries_sha256": digest(BENCH / "queries.jsonl"),
            "index_sha256": digest(args.index),
            "llm_id": args.llm_id or default_model,
            "top_n": args.top_n,
            "prompt_config_path": str(args.prompt_config) if args.prompt_config else None,
            "prompt_config_sha256": digest(args.prompt_config) if args.prompt_config else None,
            "verifier_source_path": str(args.verifier_source) if args.verifier_source else None,
            "verifier_sha256": digest(args.verifier_source) if args.verifier_source else None,
            "dialog_service_sha256": digest(DIALOG_SERVICE),
            "scope": "live RAGFlow Phase-3 on six synthetic benchmark images",
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    completed = {row["query_id"] for row in rows(result_path) if row.get("completed") and row.get("answer", "").strip() and not row["answer"].startswith("**ERROR**") } if result_path.exists() else set()
    failed = 0
    for query in (query for query in fixed_queries[:args.limit] if not selected_ids or query["id"] in selected_ids):
        if query["id"] in completed:
            continue
        expected_names = [benchmark_images[item] for item in query.get("expected_chunks", [query.get("expected_chunk")])]
        expected_ids = [index[name]["chunk_id"] for name in expected_names]
        start = time.perf_counter()
        try:
            request_body = {
                "chat_id": chat_id,
                "messages": [{"role": "user", "content": query["question"]}],
                "stream": False,
                "pass_all_history_messages": True,
                "store_history_messages": True,
            }
            if args.llm_id:
                request_body["llm_id"] = args.llm_id
            response = client.post("chat/completions", json=request_body, timeout=300)["data"] or {}
            session_id = response.get("session_id")
            if not session_id:
                raise RuntimeError("chat completion has no session_id")
            session = client.get(f"chats/{chat_id}/sessions/{session_id}", timeout=60)["data"] or {}
            reference = response.get("reference") or {}
            persisted = (session.get("reference") or [{}])[-1]
            if not isinstance(persisted, dict):
                persisted = {}
            visual = find_metadata(reference, "omnirag_multimodal")
            verification = response.get("omnirag_verification") or find_metadata(reference, "omnirag_verification")
            persisted_verification = find_metadata(persisted, "omnirag_verification")
            hit_ids = visual.get("visual_hit_chunk_ids") or []
            answer = response.get("answer") or ""
            prompt_text = response.get("prompt") or ""
            if not answer.strip() or answer.startswith("**ERROR**"):
                raise RuntimeError(f"model returned no usable answer: {answer[:300]}")
            normalized = "".join(answer.casefold().split())
            row = {
                "query_id": query["id"], "category": query["category"], "question": query["question"],
                "expected_chunk_ids": expected_ids, "expected_markers": query["expected_markers"],
                "answer": answer, "answer_markers_all_present": all("".join(marker.casefold().split()) in normalized for marker in query["expected_markers"]),
                "prompt_chars": len(prompt_text),
                "prompt_sha256": hashlib.sha256(prompt_text.encode("utf-8")).hexdigest() if prompt_text else None,
                "latency_ms": round((time.perf_counter() - start) * 1000, 1),
                "chat_id": chat_id, "session_id": session_id,
                "visual_hit_chunk_ids": hit_ids,
                "visual_recall_at_1": all(item in hit_ids[:1] for item in expected_ids),
                "visual_recall_at_5": all(item in hit_ids[:5] for item in expected_ids),
                "reference": reference,
                "verification": verification,
                "persisted_verification": persisted_verification,
                "verification_persisted": bool(verification.get("enabled") and persisted_verification == verification),
                "completed": True,
            }
        except Exception as exc:
            failed += 1
            row = {"query_id": query["id"], "question": query["question"], "completed": False,
                   "error": f"{type(exc).__name__}: {exc}", "latency_ms": round((time.perf_counter() - start) * 1000, 1)}
        with result_path.open("a", encoding="utf-8") as sink:
            sink.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"{query['id']}: {'DONE' if row['completed'] else 'ERROR'} {row['latency_ms']}ms", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
