"""Dataset integrity helpers used before any Phase-6 model training."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Iterable

from .schema import validate_router_output

_WS = re.compile(r"\s+")


def normalize_prompt(text: str) -> str:
    return _WS.sub(" ", (text or "").strip().lower())


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_jsonl(path: str | Path) -> list[dict]:
    rows = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: invalid JSON: {exc}") from exc
            rows.append(row)
    return rows


def write_jsonl(path: str | Path, rows: Iterable[dict]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def validate_rows(rows: list[dict], *, split_name: str) -> None:
    ids: set[str] = set()
    prompts: set[str] = set()
    for idx, row in enumerate(rows):
        required = {"id", "family_id", "source_type", "source_ref", "language", "prompt", "completion", "query"}
        missing = required - set(row)
        if missing:
            raise ValueError(f"{split_name}[{idx}] missing fields: {sorted(missing)}")
        if row["id"] in ids:
            raise ValueError(f"duplicate id in {split_name}: {row['id']}")
        ids.add(row["id"])
        normalized = normalize_prompt(row["prompt"])
        if normalized in prompts:
            raise ValueError(f"duplicate prompt inside {split_name}: {row['id']}")
        prompts.add(normalized)
        if row["source_type"] not in {"synthetic_template", "protected_benchmark"}:
            raise ValueError(f"unexpected source_type: {row['source_type']}")
        validate_router_output(json.loads(row["completion"]))


def ngrams(text: str, n: int = 5) -> set[tuple[str, ...]]:
    toks = normalize_prompt(text).split()
    if len(toks) < n:
        return {tuple(toks)} if toks else set()
    return {tuple(toks[i : i + n]) for i in range(len(toks) - n + 1)}


def max_ngram_overlap(reference: list[dict], candidate: dict, n: int = 5) -> float:
    cand = ngrams(candidate["query"], n=n)
    if not cand:
        return 0.0
    best = 0.0
    for row in reference:
        ref = ngrams(row["query"], n=n)
        if not ref:
            continue
        best = max(best, len(cand & ref) / max(1, len(cand)))
    return best


def leakage_report(splits: dict[str, list[dict]], protected: list[dict]) -> dict:
    for name, rows in splits.items():
        validate_rows(rows, split_name=name)
    validate_rows(protected, split_name="protected")

    family_sets = {name: {row["family_id"] for row in rows} for name, rows in splits.items()}
    prompt_sets = {name: {normalize_prompt(row["prompt"]) for row in rows} for name, rows in splits.items()}
    family_collisions = {}
    prompt_collisions = {}
    names = list(splits)
    for i, left in enumerate(names):
        for right in names[i + 1 :]:
            key = f"{left}__{right}"
            family_collisions[key] = sorted(family_sets[left] & family_sets[right])
            prompt_collisions[key] = len(prompt_sets[left] & prompt_sets[right])

    protected_norm = {normalize_prompt(row["prompt"]) for row in protected}
    exact_protected_train = len(prompt_sets.get("train", set()) & protected_norm)
    exact_protected_validation = len(prompt_sets.get("validation", set()) & protected_norm)

    return {
        "family_collisions": family_collisions,
        "prompt_collision_counts": prompt_collisions,
        "protected_exact_overlap_train": exact_protected_train,
        "protected_exact_overlap_validation": exact_protected_validation,
        "counts": {name: len(rows) for name, rows in splits.items()} | {"protected": len(protected)},
        "class_counts": {
            name: dict(sorted(Counter(json.loads(row["completion"])["query_class"] for row in rows).items()))
            for name, rows in splits.items()
        },
    }


def assert_no_leakage(report: dict) -> None:
    if any(report["family_collisions"].values()):
        raise ValueError(f"family leakage detected: {report['family_collisions']}")
    if any(report["prompt_collision_counts"].values()):
        raise ValueError(f"exact prompt leakage detected: {report['prompt_collision_counts']}")
    if report["protected_exact_overlap_train"] or report["protected_exact_overlap_validation"]:
        raise ValueError("protected benchmark prompt leaked into train/validation")
