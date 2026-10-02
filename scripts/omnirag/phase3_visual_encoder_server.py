#!/usr/bin/env python3
"""Serve a single local SigLIP2 model to the RAGFlow container."""

from __future__ import annotations

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from extensions.omnirag.multimodal.visual_encoder import Siglip2Encoder


class Handler(BaseHTTPRequestHandler):
    encoder: Siglip2Encoder
    token: str

    def _reply(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path != "/health":
            self._reply(404, {"error": "not found"})
            return
        self._reply(200, {"status": "ok", "model": self.encoder.model_name})

    def do_POST(self) -> None:
        if self.path != "/encode/text":
            self._reply(404, {"error": "not found"})
            return
        if self.headers.get("X-OmniRAG-Token") != self.token:
            self._reply(403, {"error": "forbidden"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 65536:
                raise ValueError("request size out of range")
            data = json.loads(self.rfile.read(size))
            texts = data.get("texts")
            if not isinstance(texts, list) or not 0 < len(texts) <= 16 or any(not isinstance(t, str) or len(t) > 4096 for t in texts):
                raise ValueError("texts must contain 1 to 16 short strings")
            self._reply(200, {"vectors": self.encoder.encode_texts(texts)})
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self._reply(400, {"error": str(exc)})
        except Exception:
            self._reply(500, {"error": "visual encoding failed"})
            raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=11435)
    parser.add_argument("--model", default=os.getenv("OMNIRAG_VISUAL_MODEL", "google/siglip2-base-patch16-384"))
    parser.add_argument("--device", default=os.getenv("OMNIRAG_VISUAL_DEVICE", "cuda"))
    args = parser.parse_args()
    token = os.getenv("OMNIRAG_VISUAL_ENCODER_TOKEN", "")
    if not token:
        parser.error("OMNIRAG_VISUAL_ENCODER_TOKEN is required")
    Handler.token = token
    Handler.encoder = Siglip2Encoder(model_name=args.model, device=args.device)
    print(f"SigLIP2 encoder ready on {args.host}:{args.port}", flush=True)
    HTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
