#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "omniai" / "OMNIAI_MANIFEST.json"

PREFIXES = [
    "omniai_platform",
    "services/omniai_gateway",
    "services/omniai_agent",
    "services/omniai_llamaindex",
    "services/omniai_tensorflow",
    "services/omniai_realtime_go",
    "services/omniai_bff_nest",
    "services/omniai_enterprise_spring",
    "labs/langchain_lab",
    "labs/vector_lab",
    "labs/tensorflow_lab",
    "labs/django_admin",
    "infra/omniai",
    "benchmarks/omniai",
    "docs/omniai",
    "config/omniai",
    "scripts/omniai",
    "tests/omniai",
]
EXTRA = [
    "OMNIAI.md",
    "OMNIOPS.md",
    "THIRD_PARTY_OMNIAI.md",
    "apps/omniops/run.py",
    "apps/omniops/web/app.js",
    "scripts/omnirag/run_omniops.py",
    "scripts/omnirag/omniops_selfcheck.py",
    "docs/omnirag/OMNIOPS_PRODUCT.md",
    "docs/omnirag/OMNIOPS_DELIVERY.md",
]


def wanted(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    if rel == OUT.relative_to(ROOT).as_posix():
        return False
    if any(part in {"__pycache__", "node_modules", "target", "dist"} for part in path.parts):
        return False
    return rel in EXTRA or any(rel == prefix or rel.startswith(prefix + "/") for prefix in PREFIXES)


def main() -> int:
    files = []
    for path in sorted(p for p in ROOT.rglob("*") if p.is_file() and wanted(p)):
        raw = path.read_bytes()
        files.append({
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
        })
    data = {
        "product": "OmniAI Modular Platform",
        "version": "2.0.0",
        "base": "OmniRAG-Agent + OmniOps Product V1",
        "delivery": "modular-learning-and-integration-v2",
        "runtime_verified": False,
        "verified_here": {
            "phase8_prelocal_acceptance": "PASS",
            "omnirag_plus_omniai_tests": "85 passed",
            "fastapi_http_selfcheck": "PASS",
            "external_framework_runtime": "partially_deferred"
        },
        "deferred": [
            "LangGraph isolated service runtime (package unavailable in this container)",
            "LlamaIndex isolated service runtime",
            "TensorFlow training/service runtime",
            "Go dependency build",
            "NestJS npm build",
            "Spring Maven build",
            "NATS distributed end-to-end",
            "Docker Compose multi-service runtime",
            "live RAGFlow/GPU benchmarks"
        ],
        "files": files,
    }
    OUT.write_bytes((json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    print(OUT.relative_to(ROOT))
    print(f"files={len(files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
