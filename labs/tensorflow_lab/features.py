from __future__ import annotations

KEYWORDS = ("timeout", "error", "critical", "attack", "dns", "cpu", "memory", "database")


def text_features(text: str) -> list[float]:
    lower = (text or "").lower()
    length = min(len(lower), 1000) / 1000.0
    tokens = lower.split()
    values = [length, min(len(tokens), 200) / 200.0]
    values.extend(1.0 if keyword in lower else 0.0 for keyword in KEYWORDS)
    return values
