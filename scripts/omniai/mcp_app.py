"""ASGI entry for the read-only OmniRAG reference MCP server."""

from extensions.omnirag.mcp.reference_server import build_server

app = build_server().streamable_http_app()
