"""Long-term memory selection for agent planning.

RAGFlow's memory search API returns results ordered by its own hybrid retrieval
but does not expose the raw similarity score in the public result contract.
Phase 4 therefore treats source rank as the retrieval signal instead of
inventing a similarity number. A small lexical-overlap and recency term are
added only for deterministic tie-breaking and pruning.
"""

from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Iterable

from .types import MemoryItem

_CJK_RUN_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]+")
_WORD_RE = re.compile(r"[A-Za-z0-9_\-]+")


def _tokens(text: str) -> set[str]:
    text = (text or "").lower()
    out = {m.group(0) for m in _WORD_RE.finditer(text) if len(m.group(0)) >= 2}
    for run in _CJK_RUN_RE.findall(text):
        if len(run) <= 2:
            out.add(run)
        else:
            out.update(run[i : i + 2] for i in range(len(run) - 1))
    return out


def _lexical_overlap(query: str, content: str) -> float:
    q = _tokens(query)
    c = _tokens(content)
    if not q or not c:
        return 0.0
    return len(q & c) / max(1, len(q))


def _parse_datetime(value: str) -> datetime | None:
    raw = (value or "").strip()
    if not raw:
        return None
    raw = raw.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        try:
            dt = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _recency_score(valid_at: str, now: datetime, half_life_days: float = 30.0) -> float:
    dt = _parse_datetime(valid_at)
    if dt is None:
        return 0.5
    age_days = max(0.0, (now - dt).total_seconds() / 86400.0)
    return math.exp(-math.log(2.0) * age_days / max(1.0, half_life_days))


def normalize_ragflow_memory_results(
    query: str,
    rows: Iterable[dict],
    *,
    allowed_types: tuple[str, ...] = ("procedural", "episodic"),
    now: datetime | None = None,
) -> list[MemoryItem]:
    """Normalize RAGFlow memory rows into explicit scored planning memories.

    ``source_rank`` is 1-based. The score is intentionally transparent:
    60% rank-derived relevance, 25% lexical overlap, 15% recency. Memory type is
    a hard allow-list rather than a hidden bonus.
    """

    now = now or datetime.now(timezone.utc)
    allowed = {x.lower() for x in allowed_types}
    seen: set[str] = set()
    out: list[MemoryItem] = []

    for rank, row in enumerate(rows or [], start=1):
        mtype = str(row.get("message_type") or "").lower().strip()
        content = " ".join(str(row.get("content") or "").split())
        if not content or mtype not in allowed:
            continue
        dedupe_key = re.sub(r"\s+", " ", content.lower()).strip()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        rank_score = 1.0 / math.log2(rank + 1.0)
        overlap = _lexical_overlap(query, content)
        recency = _recency_score(str(row.get("valid_at") or ""), now)
        final = 0.60 * rank_score + 0.25 * overlap + 0.15 * recency
        out.append(
            MemoryItem(
                memory_id=str(row.get("memory_id") or ""),
                message_id=str(row.get("message_id") or row.get("id") or ""),
                memory_type=mtype,
                content=content,
                valid_at=str(row.get("valid_at") or ""),
                source_rank=rank,
                rank_score=rank_score,
                lexical_overlap=overlap,
                recency_score=recency,
                final_score=final,
            )
        )

    return sorted(out, key=lambda x: (-x.final_score, x.source_rank, x.message_id))


def select_planning_memories(
    query: str,
    rows: Iterable[dict],
    *,
    allowed_types: tuple[str, ...] = ("procedural", "episodic"),
    top_n: int = 5,
    max_chars: int = 4000,
    min_score: float = 0.20,
    now: datetime | None = None,
) -> list[MemoryItem]:
    candidates = normalize_ragflow_memory_results(query, rows, allowed_types=allowed_types, now=now)
    selected: list[MemoryItem] = []
    used_chars = 0
    for item in candidates:
        if item.final_score < min_score:
            continue
        cost = len(item.content)
        if selected and used_chars + cost > max_chars:
            break
        if not selected and cost > max_chars:
            # Keep a bounded first memory rather than returning no context.
            item = MemoryItem(**{**item.as_dict(), "content": item.content[:max_chars]})
            cost = len(item.content)
        selected.append(item)
        used_chars += cost
        if len(selected) >= max(0, top_n):
            break
    return selected


def render_planning_memory_context(items: list[MemoryItem]) -> str:
    if not items:
        return ""
    lines = [
        "# Long-term planning memory (strategy context only)",
        "Use these memories only to choose research strategy or tool order. Do NOT treat them as factual evidence, do NOT cite them, and do NOT let them override retrieved sources.",
    ]
    for idx, item in enumerate(items, start=1):
        lines.append(f"- M{idx} [{item.memory_type}] {item.content}")
    return "\n".join(lines)
