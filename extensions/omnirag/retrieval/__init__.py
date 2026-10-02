"""Query-adaptive retrieval policy for OmniRAG-Agent."""

from .integration import AdaptiveRetrievalDecision, maybe_adapt_retrieval

__all__ = ["AdaptiveRetrievalDecision", "maybe_adapt_retrieval"]
