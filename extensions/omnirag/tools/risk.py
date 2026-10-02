"""Conservative risk classification for built-in and MCP tools.

MCP annotations are *advisory hints*, not a security boundary. Phase 5 keeps
those hints for audit/UI purposes, but a ``readOnlyHint`` never overrides a
name/description that looks like write or code-execution capability.
Ambiguous tools remain UNKNOWN rather than being silently treated as safe.
"""

from __future__ import annotations

import re
from typing import Any

from .types import ToolRisk


_EXECUTE_PATTERNS = (
    r"\bexec(?:ute)?\b",
    r"\bcode\b",
    r"\bshell\b",
    r"\bterminal\b",
    r"\bsql\b",
    r"\bbrowser\b",
    r"\bscript\b",
)
_WRITE_PATTERNS = (
    r"\bcreate\b",
    r"\bupdate\b",
    r"\bdelete\b",
    r"\bremove\b",
    r"\bwrite\b",
    r"\bsend\b",
    r"\bemail\b",
    r"\bupload\b",
    r"\bpost\b",
    r"\bpublish\b",
    r"\bmodify\b",
)
_READ_PATTERNS = (
    r"\bsearch\b",
    r"\bfind\b",
    r"\bget\b",
    r"\blist\b",
    r"\blookup\b",
    r"\bretrieve\b",
    r"\bquery\b",
    r"\bread\b",
    r"\bweather\b",
    r"\bwikipedia\b",
    r"\barxiv\b",
    r"\bpubmed\b",
)

_EXECUTE_TERMS_CJK = ("执行", "运行代码", "代码执行", "命令行", "终端", "脚本", "浏览器自动化")
_WRITE_TERMS_CJK = ("创建", "新增", "更新", "删除", "移除", "写入", "发送", "邮件", "上传", "发布", "修改")
_READ_TERMS_CJK = ("搜索", "检索", "查找", "查询", "获取", "读取", "列出", "天气", "百科")


def _annotation_bool(annotations: dict[str, Any], key: str) -> bool | None:
    value = annotations.get(key)
    return value if isinstance(value, bool) else None


def _matches(text: str, patterns: tuple[str, ...], cjk_terms: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns) or any(term in text for term in cjk_terms)


def classify_tool_risk(
    name: str,
    description: str = "",
    annotations: dict[str, Any] | None = None,
) -> tuple[ToolRisk, dict[str, bool | None]]:
    """Classify a tool without trusting MCP annotations as authorization.

    Order is intentionally conservative:
      1. explicit ``destructiveHint=True`` is treated as write risk;
      2. execute/write lexical evidence overrides ``readOnlyHint=True``;
      3. read lexical evidence can establish read risk;
      4. only otherwise may ``readOnlyHint=True`` serve as a weak read hint;
      5. everything else is UNKNOWN and denied by the default policy.
    """

    annotations = dict(annotations or {})
    read_only = _annotation_bool(annotations, "readOnlyHint")
    destructive = _annotation_bool(annotations, "destructiveHint")
    idempotent = _annotation_bool(annotations, "idempotentHint")
    open_world = _annotation_bool(annotations, "openWorldHint")

    text = f"{name} {description}".lower().replace("_", " ").replace("-", " ")

    if destructive is True:
        risk = ToolRisk.WRITE
    elif _matches(text, _EXECUTE_PATTERNS, _EXECUTE_TERMS_CJK):
        risk = ToolRisk.EXECUTE
    elif _matches(text, _WRITE_PATTERNS, _WRITE_TERMS_CJK):
        risk = ToolRisk.WRITE
    elif _matches(text, _READ_PATTERNS, _READ_TERMS_CJK):
        risk = ToolRisk.READ
    elif read_only is True:
        # Advisory-only fallback. It cannot downgrade lexical write/execute
        # evidence because those branches have already been evaluated above.
        risk = ToolRisk.READ
    else:
        risk = ToolRisk.UNKNOWN

    return risk, {
        "read_only": read_only,
        "destructive": destructive,
        "idempotent": idempotent,
        "open_world": open_world,
    }
