import asyncio
from dataclasses import dataclass

import pytest

from extensions.omnirag.tools.policy import ToolPolicy
from extensions.omnirag.tools.registry import ToolRegistry
from extensions.omnirag.tools.selector import ToolSelectorV1
from extensions.omnirag.tools.session import GovernedToolCallSession
from extensions.omnirag.tools.types import ToolDescriptor, ToolRisk, ToolSource


class FakeBuiltinTool:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def get_meta(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
            },
        }


@dataclass
class FakeServer:
    id: str
    variables: dict


class FakeMcpSession:
    def __init__(self, server):
        self._mcp_server = server


@dataclass(frozen=True)
class FakeBinding:
    session: object
    original_name: str


class AsyncBaseSession:
    def __init__(self):
        self.calls = []

    async def tool_call_async(self, name, arguments, request_timeout=None):
        self.calls.append((name, dict(arguments), request_timeout))
        return {"ok": True, "name": name}


def test_registry_preserves_mcp_annotations_and_source():
    server = FakeServer(
        id="srv-1",
        variables={
            "tools": {
                "lookup_device": {
                    "description": "Lookup one device",
                    "inputSchema": {"type": "object", "properties": {"device_id": {"type": "string"}}, "required": ["device_id"]},
                    "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True},
                }
            }
        },
    )
    tools = {"lookup_device_0": FakeBinding(FakeMcpSession(server), "lookup_device")}
    meta = [
        {
            "type": "function",
            "function": {
                "name": "lookup_device_0",
                "description": "Lookup one device",
                "parameters": {"type": "object", "properties": {"device_id": {"type": "string"}}, "required": ["device_id"]},
            },
        }
    ]
    reg = ToolRegistry.from_ragflow(tools, meta)
    item = reg.get("lookup_device_0")
    assert item.source.value == "mcp"
    assert item.source_id == "srv-1"
    assert item.risk == ToolRisk.READ
    assert item.read_only is True
    assert item.destructive is False


def test_selector_prefers_relevant_read_tool_and_filters_execute_tool():
    tools = {
        "search_docs_0": FakeBuiltinTool("search_docs", "Search and retrieve relevant documents"),
        "execute_code_1": FakeBuiltinTool("execute_code", "Execute Python code in a sandbox"),
        "weather_2": FakeBuiltinTool("weather", "Get weather forecast and temperature"),
    }
    meta = []
    for indexed, obj in tools.items():
        m = obj.get_meta()
        m["function"]["name"] = indexed
        meta.append(m)
    reg = ToolRegistry.from_ragflow(tools, meta)
    sel = ToolSelectorV1().select("Find the relevant document about the contract", reg, ToolPolicy())
    assert sel.selected_names[0] == "search_docs_0"
    assert "execute_code_1" in sel.rejected_by_policy


def test_selector_chinese_query_matches_weather_capability():
    tools = {
        "weather_0": FakeBuiltinTool("weather_forecast", "查询天气、气温和天气预报"),
        "search_1": FakeBuiltinTool("search_docs", "搜索企业知识库文档"),
    }
    meta = []
    for indexed, obj in tools.items():
        m = obj.get_meta()
        m["function"]["name"] = indexed
        meta.append(m)
    reg = ToolRegistry.from_ragflow(tools, meta)
    sel = ToolSelectorV1().select("查询东京明天的天气预报", reg, ToolPolicy())
    assert sel.selected_names[0] == "weather_0"


def test_governed_session_validates_schema_and_budget():
    tool = FakeBuiltinTool("search_docs", "Search documents")
    meta = [tool.get_meta()]
    meta[0]["function"]["name"] = "search_docs_0"
    reg = ToolRegistry.from_ragflow({"search_docs_0": tool}, meta)
    base = AsyncBaseSession()
    policy = ToolPolicy(max_total_calls=1, max_calls_per_tool=1)
    session = GovernedToolCallSession(base, reg, ("search_docs_0",), policy)

    result = asyncio.run(session.tool_call_async("search_docs_0", {"query": "x"}))
    assert result["ok"] is True
    assert len(session.trace_snapshot()) == 1
    assert session.trace_snapshot()[0]["argument_keys"] == ["query"]
    assert "x" not in str(session.trace_snapshot()[0])

    with pytest.raises(RuntimeError, match="budget exhausted"):
        asyncio.run(session.tool_call_async("search_docs_0", {"query": "y"}))


def test_governed_session_rejects_missing_required_argument_before_execution():
    tool = FakeBuiltinTool("search_docs", "Search documents")
    meta = [tool.get_meta()]
    meta[0]["function"]["name"] = "search_docs_0"
    reg = ToolRegistry.from_ragflow({"search_docs_0": tool}, meta)
    base = AsyncBaseSession()
    session = GovernedToolCallSession(base, reg, ("search_docs_0",), ToolPolicy())
    with pytest.raises(Exception):
        asyncio.run(session.tool_call_async("search_docs_0", {}))
    assert base.calls == []
    assert session.trace_snapshot()[-1]["ok"] is False


def test_governed_session_denies_tool_outside_shortlist():
    tools = {
        "search_docs_0": FakeBuiltinTool("search_docs", "Search documents"),
        "weather_1": FakeBuiltinTool("weather", "Get weather forecast"),
    }
    meta = []
    for indexed, obj in tools.items():
        m = obj.get_meta()
        m["function"]["name"] = indexed
        meta.append(m)
    reg = ToolRegistry.from_ragflow(tools, meta)
    base = AsyncBaseSession()
    session = GovernedToolCallSession(base, reg, ("search_docs_0",), ToolPolicy())
    with pytest.raises(PermissionError, match="outside the per-query shortlist"):
        asyncio.run(session.tool_call_async("weather_1", {"query": "Tokyo"}))
    assert base.calls == []


def test_integration_clears_empty_shortlist_and_restores_native_binding(monkeypatch):
    from extensions.omnirag.tools.integration import prepare_agent_tools

    class Mdl:
        def __init__(self):
            self.tools = [{"stale": True}]
            self.toolcall_session = object()

    class Chat:
        def __init__(self):
            self.mdl = Mdl()
            self.bindings = []

        def bind_tools(self, session, schemas):
            self.bindings.append((session, schemas))
            self.mdl.toolcall_session = session
            self.mdl.tools = schemas

    class Agent:
        def __init__(self):
            self.tools = {"execute_code_0": FakeBuiltinTool("execute_code", "Execute Python code")}
            m = self.tools["execute_code_0"].get_meta()
            m["function"]["name"] = "execute_code_0"
            self.tool_meta = [m]
            self.toolcall_session = AsyncBaseSession()
            self.chat_mdl = Chat()
            self._param = type("P", (), {"prompts": []})()
            self._canvas = type("C", (), {"globals": {"sys.query": "run code"}})()
            self.outputs = {}

        def set_output(self, key, value):
            self.outputs[key] = value

    agent = Agent()
    monkeypatch.setenv("OMNIRAG_TOOL_GOVERNANCE", "1")
    monkeypatch.setenv("OMNIRAG_TOOL_ALLOWED_RISKS", "read")
    meta = prepare_agent_tools(agent, "run code")
    assert meta["selected"] == []
    assert agent.chat_mdl.mdl.tools == []

    monkeypatch.setenv("OMNIRAG_TOOL_GOVERNANCE", "0")
    disabled = prepare_agent_tools(agent, "run code")
    assert disabled["enabled"] is False
    assert agent.chat_mdl.mdl.tools == agent.tool_meta


def test_mcp_readonly_annotation_cannot_downgrade_destructive_name():
    server = FakeServer(
        id="srv-danger",
        variables={
            "tools": {
                "delete_records": {
                    "description": "Delete matching records from the remote service",
                    "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}},
                    # Annotations are advisory; this contradictory hint must not
                    # turn a destructive-looking tool into a read tool.
                    "annotations": {"readOnlyHint": True, "destructiveHint": False},
                }
            }
        },
    )
    tools = {"delete_records_0": FakeBinding(FakeMcpSession(server), "delete_records")}
    meta = [
        {
            "type": "function",
            "function": {
                "name": "delete_records_0",
                "description": "Delete matching records from the remote service",
                "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
            },
        }
    ]
    reg = ToolRegistry.from_ragflow(tools, meta)
    assert reg.get("delete_records_0").risk == ToolRisk.WRITE
    assert ToolPolicy().permits(reg.get("delete_records_0"))[0] is False


def test_default_policy_denies_explicit_open_world_hint():
    descriptor = ToolRegistry(
        [
            ToolDescriptor(
                name="web_lookup_0",
                original_name="lookup",
                description="Lookup public information",
                parameters={"type": "object", "properties": {}},
                source=ToolSource.MCP,
                risk=ToolRisk.READ,
                open_world=True,
            )
        ]
    ).get("web_lookup_0")
    ok, reason = ToolPolicy().permits(descriptor)
    assert ok is False
    assert "open-world" in reason


def test_schema_validation_error_does_not_echo_argument_value_into_audit_trace():
    class EnumTool(FakeBuiltinTool):
        def get_meta(self):
            return {
                "type": "function",
                "function": {
                    "name": self.name,
                    "description": self.description,
                    "parameters": {
                        "type": "object",
                        "properties": {"query": {"type": "string", "enum": ["allowed"]}},
                        "required": ["query"],
                    },
                },
            }

    tool = EnumTool("search_docs", "Search documents")
    meta = [tool.get_meta()]
    meta[0]["function"]["name"] = "search_docs_0"
    reg = ToolRegistry.from_ragflow({"search_docs_0": tool}, meta)
    base = AsyncBaseSession()
    session = GovernedToolCallSession(base, reg, ("search_docs_0",), ToolPolicy())
    secretish = "private-query-value"
    with pytest.raises(ValueError, match="JSON Schema validation"):
        asyncio.run(session.tool_call_async("search_docs_0", {"query": secretish}))
    snapshot = session.trace_snapshot()
    assert secretish not in str(snapshot)
    assert snapshot[-1]["error_type"] == "ValueError"
    assert "arguments_hmac_sha256" in snapshot[-1]
