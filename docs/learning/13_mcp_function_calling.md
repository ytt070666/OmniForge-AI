# MCP 与 Function Calling

## 解决的问题

让工具能力可发现、可调用且受策略约束。

## 核心原理

Function Calling 是模型输出调用意图；MCP 规定工具发现与传输；ToolPolicy 执行授权。

## 本项目代码位置

extensions/omnirag/mcp/reference_server.py；extensions/omnirag/tools/policy.py

## 如何运行

运行 .venv-agent\Scripts\python.exe scripts/omniai/smoke_mcp.py。

## 如何测试

streamable HTTP tools/list、3 个工具调用通过；ToolPolicy 10 项测试通过。

## 与其他技术的关系

LangGraph 可编排工具，但不能以 MCP annotation 作为授权。

## 常见面试题

为何默认拒绝 WRITE？答：安全策略只允许 READ。MCP 是否等于授权？答：不是。

## 当前真实运行状态

PASS：真实 MCP 传输与默认拒绝策略测试。
