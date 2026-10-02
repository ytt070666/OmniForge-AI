"""Deterministic query features used by the first adaptive retrieval policy.

The first research iteration is deliberately transparent and reproducible. It
uses inspectable features rather than an opaque LLM router. A learned router can
replace this module later while keeping the same decision interface.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict

_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
_IDENTIFIER_RE = re.compile(r"(?:\b[A-Z]{2,}[A-Z0-9_-]*\d[A-Z0-9_-]*\b|\b\d{3,6}\b|\b\w+-\w*\d\w*\b)")
_QUOTED_RE = re.compile(r"['\"`][^'\"`]{2,}['\"`]")

_VISUAL_TERMS = {
    "figure", "fig.", "image", "picture", "chart", "diagram", "screenshot",
    "table", "topology", "plot", "graph", "visual", "page image",
    "图", "图片", "图像", "图表", "示意图", "流程图", "截图", "表格", "拓扑", "曲线",
}
_LEXICAL_TERMS = {
    "exact", "identifier", "id", "code", "port", "version", "uuid", "hash",
    "serial", "sku", "cve", "ip", "url", "filename", "file name",
    "准确", "精确", "编号", "标识符", "端口", "版本", "序列号", "文件名", "哈希",
}
_SEMANTIC_TERMS = {
    "why", "how", "explain", "meaning", "approach", "reason", "compare",
    "relationship", "different words", "same meaning", "summarize", "concept",
    "为什么", "如何", "解释", "原因", "比较", "关系", "含义", "概念", "总结",
}


def _contains_any(text: str, terms: set[str]) -> bool:
    """Match English terms on token/phrase boundaries and CJK terms by substring.

    Plain substring matching makes short signals such as ``id`` match ``grid``
    and ``table`` match ``stable``. Those false positives would bias the router,
    so ASCII terms use conservative word boundaries.
    """
    lower = text.lower()
    for term in terms:
        needle = term.lower()
        if _CJK_RE.search(needle):
            if needle in lower:
                return True
            continue
        pattern = rf"(?<![A-Za-z0-9_]){re.escape(needle)}(?![A-Za-z0-9_])"
        if re.search(pattern, lower):
            return True
    return False


@dataclass(frozen=True)
class QueryFeatures:
    text: str
    length: int
    token_estimate: int
    contains_cjk: bool
    contains_identifier: bool
    contains_quoted_phrase: bool
    visual_signal: bool
    lexical_signal: bool
    semantic_signal: bool
    question_mark: bool

    def as_dict(self) -> dict:
        return asdict(self)


def extract_query_features(text: str) -> QueryFeatures:
    normalized = " ".join((text or "").strip().split())
    return QueryFeatures(
        text=normalized,
        length=len(normalized),
        token_estimate=max(1, len(normalized.split())),
        contains_cjk=bool(_CJK_RE.search(normalized)),
        contains_identifier=bool(_IDENTIFIER_RE.search(normalized)),
        contains_quoted_phrase=bool(_QUOTED_RE.search(normalized)),
        visual_signal=_contains_any(normalized, _VISUAL_TERMS),
        lexical_signal=_contains_any(normalized, _LEXICAL_TERMS),
        semantic_signal=_contains_any(normalized, _SEMANTIC_TERMS),
        question_mark=("?" in normalized or "？" in normalized),
    )
