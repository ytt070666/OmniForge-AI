"""Load image bytes for visually retrieved RAGFlow chunks."""

from __future__ import annotations

import asyncio
import base64
import os
from collections.abc import Callable


def _parse_image_id(image_id: str) -> tuple[str, str] | None:
    parts = (image_id or "").split("-", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return None
    return parts[0], parts[1]


def _mime(blob: bytes) -> str:
    if blob.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if blob.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if blob[:6] in {b"GIF87a", b"GIF89a"}:
        return "image/gif"
    if blob.startswith(b"RIFF") and b"WEBP" in blob[:16]:
        return "image/webp"
    return "image/jpeg"


def to_data_uri(blob: bytes) -> str:
    return f"data:{_mime(blob)};base64,{base64.b64encode(blob).decode('ascii')}"


async def load_retrieved_image_bytes(
    chunks: list[dict],
    storage_get: Callable,
    max_images: int | None = None,
) -> list[bytes]:
    """Fetch top-ranked unique chunk images from RAGFlow object storage."""

    limit = max_images if max_images is not None else int(os.getenv("OMNIRAG_MAX_RETRIEVED_IMAGES", "4"))
    if limit <= 0:
        return []
    ids: list[tuple[str, str]] = []
    seen: set[str] = set()
    for chunk in chunks:
        image_id = str(chunk.get("image_id") or chunk.get("img_id") or "")
        if not image_id or image_id in seen:
            continue
        parsed = _parse_image_id(image_id)
        if not parsed:
            continue
        seen.add(image_id)
        ids.append(parsed)
        if len(ids) >= limit:
            break

    async def get_one(bucket: str, key: str):
        try:
            return await asyncio.to_thread(storage_get, bucket=bucket, fnm=key)
        except TypeError:
            # Some storage implementations expose positional arguments.
            return await asyncio.to_thread(storage_get, bucket, key)

    blobs = await asyncio.gather(*(get_one(bucket, key) for bucket, key in ids), return_exceptions=True)
    return [bytes(blob) for blob in blobs if isinstance(blob, (bytes, bytearray)) and blob]
