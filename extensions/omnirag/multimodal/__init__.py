"""OmniRAG multimodal retrieval extension.

The package is intentionally isolated from RAGFlow core so it can be unit-tested
without booting MySQL/Elasticsearch/MinIO. Core integration is enabled only by
an explicit Phase-3 patch and environment flags.
"""

from .fusion import fuse_text_and_visual
from .router import ModalityDecision, ModalityRouterV1
from .types import FusedCandidate, VisualHit, VisualRecord

__all__ = [
    "FusedCandidate",
    "ModalityDecision",
    "ModalityRouterV1",
    "VisualHit",
    "VisualRecord",
    "fuse_text_and_visual",
]
