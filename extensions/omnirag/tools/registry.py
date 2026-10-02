"""Normalize RAGFlow built-in and MCP tool metadata into one registry."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .risk import classify_tool_risk
from .types import ToolDescriptor, ToolSource


def _mcp_raw_metadata(tool_obj: object, original_name: str) -> tuple[str, dict[str, Any]]:
    """Best-effort raw MCP metadata without opening a new transport session."""

    session = getattr(tool_obj, "session", None)
    server = getattr(session, "_mcp_server", None)
    if server is None:
        return "", {}
    server_id = str(getattr(server, "id", "") or "")

    variables = getattr(server, "variables", None)
    if not isinstance(variables, Mapping):
        variables = getattr(session, "_server_variables", None)
    if not isinstance(variables, Mapping):
        return server_id, {}

    tools = variables.get("tools")
    if not isinstance(tools, Mapping):
        return server_id, {}
    raw = tools.get(original_name)
    return server_id, dict(raw) if isinstance(raw, Mapping) else {}


def _original_name(tool_obj: object, indexed_name: str) -> str:
    name = getattr(tool_obj, "original_name", None)
    if isinstance(name, str) and name:
        return name
    try:
        meta = tool_obj.get_meta()
        fn = meta.get("function", {}) if isinstance(meta, dict) else {}
        raw = fn.get("name")
        if isinstance(raw, str) and raw:
            return raw
    except Exception:
        pass
    return indexed_name


class ToolRegistry:
    """Immutable-ish runtime registry keyed by the exact LLM-visible name."""

    def __init__(self, descriptors: list[ToolDescriptor]):
        self._descriptors = {d.name: d for d in descriptors}
        if len(self._descriptors) != len(descriptors):
            raise ValueError("Duplicate LLM-visible tool names are not allowed")

    @classmethod
    def from_ragflow(cls, tools_map: Mapping[str, object], tool_meta: list[dict[str, Any]]) -> "ToolRegistry":
        schema_by_name = {}
        for item in tool_meta or []:
            fn = item.get("function", {}) if isinstance(item, dict) else {}
            name = fn.get("name")
            if isinstance(name, str) and name:
                schema_by_name[name] = fn

        descriptors: list[ToolDescriptor] = []
        for indexed_name, tool_obj in tools_map.items():
            fn = schema_by_name.get(indexed_name, {})
            original_name = _original_name(tool_obj, indexed_name)

            is_mcp = hasattr(tool_obj, "session") and hasattr(tool_obj, "original_name")
            source = ToolSource.MCP if is_mcp else ToolSource.BUILTIN
            source_id = ""
            raw_meta: dict[str, Any] = {}
            if is_mcp:
                source_id, raw_meta = _mcp_raw_metadata(tool_obj, original_name)

            annotations = raw_meta.get("annotations", {}) if isinstance(raw_meta.get("annotations"), Mapping) else {}
            description = str(fn.get("description") or raw_meta.get("description") or "")
            parameters = fn.get("parameters") or raw_meta.get("inputSchema") or {"type": "object", "properties": {}}
            if not isinstance(parameters, dict):
                parameters = {"type": "object", "properties": {}}

            risk, hints = classify_tool_risk(original_name, description, dict(annotations))
            descriptors.append(
                ToolDescriptor(
                    name=indexed_name,
                    original_name=original_name,
                    description=description,
                    parameters=parameters,
                    source=source,
                    source_id=source_id,
                    risk=risk,
                    read_only=hints["read_only"],
                    destructive=hints["destructive"],
                    idempotent=hints["idempotent"],
                    open_world=hints["open_world"],
                    annotations=dict(annotations),
                )
            )
        return cls(descriptors)

    def get(self, name: str) -> ToolDescriptor | None:
        return self._descriptors.get(name)

    def all(self) -> tuple[ToolDescriptor, ...]:
        return tuple(self._descriptors.values())

    def schemas(self, names: set[str] | tuple[str, ...] | list[str]) -> list[dict[str, Any]]:
        return [self._descriptors[name].to_openai_tool() for name in names if name in self._descriptors]

    def public_inventory(self) -> list[dict[str, Any]]:
        return [d.public_dict() for d in self._descriptors.values()]
