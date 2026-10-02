"""Conservative data hygiene utilities for Phase-6 training datasets."""

from __future__ import annotations

import re
from dataclasses import dataclass

_PATTERNS = {
    "email": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    "ipv4": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "bearer": re.compile(r"\bBearer\s+[A-Za-z0-9._~+\-/]+=*", re.I),
    "api_key": re.compile(r"\b(?:sk|api|key)[-_]?[A-Za-z0-9]{16,}\b", re.I),
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}


@dataclass(frozen=True)
class HygieneFinding:
    kind: str
    start: int
    end: int


def findings(text: str) -> list[HygieneFinding]:
    out: list[HygieneFinding] = []
    for kind, pattern in _PATTERNS.items():
        for match in pattern.finditer(text or ""):
            # RFC1918-like IPs can be legitimate benchmark fixtures; still report
            # rather than silently delete so the dataset owner must decide.
            out.append(HygieneFinding(kind=kind, start=match.start(), end=match.end()))
    return sorted(out, key=lambda x: (x.start, x.end, x.kind))


def redact(text: str) -> str:
    value = text or ""
    replacements: list[tuple[int, int, str]] = []
    for item in findings(value):
        replacements.append((item.start, item.end, f"<REDACTED_{item.kind.upper()}>"))
    for start, end, token in reversed(replacements):
        value = value[:start] + token + value[end:]
    return value
