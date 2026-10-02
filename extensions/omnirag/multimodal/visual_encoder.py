"""Joint text-image encoder interface and an optional SigLIP2 implementation."""

from __future__ import annotations

import hashlib
import json
import math
import os
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Protocol
from urllib.request import Request, urlopen


class VisualTextEncoder(Protocol):
    def encode_texts(self, texts: list[str]) -> list[list[float]]: ...

    def encode_images(self, image_paths: list[str]) -> list[list[float]]: ...


def _normalize(v: Iterable[float]) -> list[float]:
    vals = [float(x) for x in v]
    n = math.sqrt(sum(x * x for x in vals))
    if n <= 0:
        raise ValueError("encoder returned a zero vector")
    return [x / n for x in vals]


class HashEncoderForTests:
    """Deterministic plumbing-only encoder; never use it for research metrics."""

    def __init__(self, dim: int = 32):
        self.dim = int(dim)

    def _hash(self, payload: bytes) -> list[float]:
        out: list[float] = []
        counter = 0
        while len(out) < self.dim:
            digest = hashlib.sha256(payload + counter.to_bytes(4, "big")).digest()
            for b in digest:
                out.append((float(b) - 127.5) / 127.5)
                if len(out) >= self.dim:
                    break
            counter += 1
        return _normalize(out)

    def encode_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._hash(("text:" + t).encode("utf-8")) for t in texts]

    def encode_images(self, image_paths: list[str]) -> list[list[float]]:
        return [self._hash(b"image:" + Path(p).read_bytes()) for p in image_paths]


class Siglip2Encoder:
    """Lazy Hugging Face SigLIP2 wrapper.

    No transformers/torch import happens until this class is instantiated. That
    keeps RAGFlow's baseline environment untouched while allowing a true joint
    text-image embedding model during the later local run.
    """

    def __init__(self, model_name: str | None = None, device: str | None = None):
        try:
            import torch
            from transformers import AutoModel, AutoProcessor
        except ImportError as exc:
            raise RuntimeError(
                "Siglip2Encoder requires torch + transformers. Install the optional Phase-3 visual dependencies before building a real visual index."
            ) from exc

        self._torch = torch
        self.model_name = model_name or os.getenv("OMNIRAG_VISUAL_MODEL", "google/siglip2-base-patch16-384")
        self.device = device or os.getenv("OMNIRAG_VISUAL_DEVICE") or ("cuda" if torch.cuda.is_available() else "cpu")
        self.processor = AutoProcessor.from_pretrained(self.model_name)
        self.model = AutoModel.from_pretrained(self.model_name).to(self.device).eval()
        if not hasattr(self.model, "get_text_features") or not hasattr(self.model, "get_image_features"):
            raise RuntimeError(f"{self.model_name!r} does not expose SigLIP-style joint feature methods")

    def _move(self, batch: dict) -> dict:
        return {k: v.to(self.device) if hasattr(v, "to") else v for k, v in batch.items()}

    def _vectors(self, output) -> list[list[float]]:
        # Transformers 5 returns a model output; older releases returned a tensor.
        feats = output if isinstance(output, self._torch.Tensor) else getattr(output, "pooler_output", None)
        if feats is None or feats.ndim != 2:
            raise TypeError("SigLIP2 feature output has no batched pooled embeddings")
        return [_normalize(row) for row in feats.detach().float().cpu().tolist()]

    def encode_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        batch = self.processor(text=texts, padding="max_length", truncation=True, return_tensors="pt")
        batch = self._move(batch)
        with self._torch.inference_mode():
            feats = self.model.get_text_features(**batch)
        return self._vectors(feats)

    def encode_images(self, image_paths: list[str]) -> list[list[float]]:
        if not image_paths:
            return []
        from PIL import Image

        images = []
        try:
            for path in image_paths:
                images.append(Image.open(path).convert("RGB"))
            batch = self.processor(images=images, return_tensors="pt")
            batch = self._move(batch)
            with self._torch.inference_mode():
                feats = self.model.get_image_features(**batch)
            return self._vectors(feats)
        finally:
            for image in images:
                image.close()


class HttpVisualTextEncoder:
    """Query a local, persistently loaded visual encoder process."""

    def __init__(self, endpoint: str, token: str):
        if not endpoint.startswith("http://") or not token:
            raise ValueError("local visual encoder requires an HTTP endpoint and token")
        self.endpoint = endpoint.rstrip("/")
        self.token = token

    def encode_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        payload = json.dumps({"texts": texts}, ensure_ascii=False).encode("utf-8")
        req = Request(
            f"{self.endpoint}/encode/text",
            data=payload,
            headers={"Content-Type": "application/json", "X-OmniRAG-Token": self.token},
            method="POST",
        )
        with urlopen(req, timeout=120) as response:
            vectors = json.load(response).get("vectors")
        if not isinstance(vectors, list) or len(vectors) != len(texts):
            raise ValueError("visual encoder returned the wrong vector count")
        return [_normalize(vector) for vector in vectors]

    def encode_images(self, image_paths: list[str]) -> list[list[float]]:
        raise RuntimeError("build the image index in the host encoder environment")


@lru_cache(maxsize=2)
def _siglip2_from_config(model_name: str | None, device: str | None) -> Siglip2Encoder:
    return Siglip2Encoder(model_name=model_name, device=device)


def encoder_from_env() -> VisualTextEncoder:
    kind = os.getenv("OMNIRAG_VISUAL_ENCODER", "siglip2").strip().lower()
    if kind in {"hash", "test", "deterministic"}:
        return HashEncoderForTests(dim=int(os.getenv("OMNIRAG_TEST_VISUAL_DIM", "32")))
    if kind in {"siglip2", "siglip"}:
        return _siglip2_from_config(os.getenv("OMNIRAG_VISUAL_MODEL"), os.getenv("OMNIRAG_VISUAL_DEVICE"))
    if kind == "http":
        return HttpVisualTextEncoder(
            os.getenv("OMNIRAG_VISUAL_ENCODER_URL", ""),
            os.getenv("OMNIRAG_VISUAL_ENCODER_TOKEN", ""),
        )
    raise ValueError(f"Unsupported OMNIRAG_VISUAL_ENCODER={kind!r}")
