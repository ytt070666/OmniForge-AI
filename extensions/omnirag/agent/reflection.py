"""Bounded reflection query generation from explicit evidence gaps."""

from __future__ import annotations

import re


def _clean(text: str, limit: int = 260) -> str:
    text = " ".join((text or "").split())
    return text[:limit].strip()


class ReflectionQueryV1:
    """Build a follow-up query only from already-observed gaps.

    The rewriter intentionally does not invent entities, dates, or candidate
    facts. It preserves the original task and names unsupported claims or SCA
    missing targets as the research focus.
    """

    name = "reflection_query_v1"

    def build(
        self,
        original_query: str,
        *,
        missing_targets: tuple[str, ...] = (),
        conflicts: tuple[str, ...] = (),
        feedback: str = "",
    ) -> str:
        original = _clean(original_query, 360)
        targets: list[str] = []
        seen: set[str] = set()
        for raw in [*missing_targets, *conflicts]:
            item = _clean(raw)
            key = item.lower()
            if item and key not in seen:
                seen.add(key)
                targets.append(item)
            if len(targets) >= 4:
                break

        if targets:
            focus = "; ".join(targets)
            query = (
                f"Answer the original question: {original}. "
                f"Retrieve direct source evidence specifically to resolve these unresolved points: {focus}. "
                "Do not assume the missing facts; verify them from the available sources."
            )
        elif feedback:
            query = (
                f"Answer the original question: {original}. "
                f"Use another evidence search focused on this stated gap: {_clean(feedback, 300)}. "
                "Verify the gap from source evidence before answering."
            )
        else:
            query = (
                f"Answer the original question: {original}. "
                "Run one additional evidence search from a different angle and verify every material claim from source evidence."
            )
        return re.sub(r"\s+", " ", query).strip()[:900]


def query_signature(text: str) -> str:
    """Stable coarse signature used to stop reflection loops."""
    lowered = (text or "").lower()
    return " ".join(re.findall(r"[a-z0-9_\-]+|[\u3400-\u9fff]", lowered))[:1200]
