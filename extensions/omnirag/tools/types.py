"""Shared types for Phase-5 tool governance.

The types are intentionally independent from RAGFlow internals so they can be
unit tested without opening MCP sessions or loading a model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ToolSource(StrEnum):
    BUILTIN = "builtin"
    MCP = "mcp"


class ToolRisk(StrEnum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ToolDescriptor:
    """Normalized metadata for one tool name visible to the LLM."""

    name: str
    original_name: str
    description: str
    parameters: dict[str, Any]
    source: ToolSource
    source_id: str = ""
    risk: ToolRisk = ToolRisk.UNKNOWN
    read_only: bool | None = None
    destructive: bool | None = None
    idempotent: bool | None = None
    open_world: bool | None = None
    annotations: dict[str, Any] = field(default_factory=dict)

    def to_openai_tool(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def public_dict(self) -> dict[str, Any]:
        """Safe metadata for logs/UI; deliberately excludes credentials."""

        return {
            "name": self.name,
            "original_name": self.original_name,
            "description": self.description,
            "source": self.source.value,
            "source_id": self.source_id,
            "risk": self.risk.value,
            "read_only": self.read_only,
            "destructive": self.destructive,
            "idempotent": self.idempotent,
            "open_world": self.open_world,
        }


@dataclass(frozen=True)
class ToolSelection:
    query: str
    selected_names: tuple[str, ...]
    rejected_by_policy: tuple[str, ...]
    scores: dict[str, float]
    fallback_used: bool = False


@dataclass(frozen=True)
class ToolCallEvent:
    tool_name: str
    source: str
    risk: str
    ok: bool
    elapsed_seconds: float
    argument_keys: tuple[str, ...]
    # HMAC-SHA256 with an ephemeral per-session key. Unlike a raw SHA-256 of
    # the arguments, this is resistant to simple offline dictionary guessing.
    arguments_hmac_sha256: str
    error_type: str = ""
