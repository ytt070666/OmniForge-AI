# OmniAI LangGraph Agent Service

This service makes LangGraph a real orchestration layer rather than a dependency
name in a resume. It injects OmniOps/OmniRAG domain callbacks into a state graph:

`classify -> retrieve -> tool -> generate -> verify -> retry|finish`

The verifier remains authoritative for the decision, the retry count is bounded,
and the tool callback only exposes the existing read-only reference tools.

Use a separate virtual environment from the RAGFlow service to avoid dependency
collisions with RAGFlow's own pinned LangGraph stack.
