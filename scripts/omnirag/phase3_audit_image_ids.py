#!/usr/bin/env python3
"""Verify that every visual index row points to the original RAGFlow image bytes."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path

import requests
from PIL import Image, ImageChops, ImageStat

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "benchmarks" / "omnirag" / "phase3" / "assets"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--auth-file", type=Path, required=True)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--api-root", default="http://127.0.0.1:9380/api/v1")
    args = parser.parse_args()
    auth = json.loads(args.auth_file.read_text(encoding="utf-8-sig"))
    records = [json.loads(line) for line in args.index.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(records) != 6 or len({row["image_id"] for row in records}) != 6:
        raise RuntimeError("expected six distinct RAGFlow image IDs")

    results = []
    for record in records:
        name = record["document_name"]
        source_path = ASSETS / name
        if source_path.parent != ASSETS or not source_path.is_file():
            raise RuntimeError(f"missing source asset: {name}")
        response = requests.get(
            f"{args.api_root.rstrip('/')}/documents/images/{record['image_id']}",
            headers={"Authorization": f"Bearer {auth['api_key']}"},
            timeout=30,
        )
        response.raise_for_status()
        with Image.open(source_path) as source_image, Image.open(io.BytesIO(response.content)) as stored_image:
            source = source_image.convert("RGB")
            stored = stored_image.convert("RGB")
            if source.size != stored.size:
                raise RuntimeError(f"image dimensions differ for {name}: {source.size} != {stored.size}")
            mae = sum(ImageStat.Stat(ImageChops.difference(source, stored)).mean) / 3
        if mae > 5:
            raise RuntimeError(f"stored image differs materially from {name}: MAE={mae:.3f}")
        results.append({
            "document_name": name,
            "document_id": record["document_id"],
            "chunk_id": record["chunk_id"],
            "image_id": record["image_id"],
            "dimensions": list(source.size),
            "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
            "ragflow_image_sha256": hashlib.sha256(response.content).hexdigest(),
            "mean_absolute_pixel_error": round(mae, 4),
        })
        print(f"{name}: image_id={record['image_id']} MAE={mae:.4f}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"status": "PASS", "images": results}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
