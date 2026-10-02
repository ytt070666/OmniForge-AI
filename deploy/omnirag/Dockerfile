ARG RAGFLOW_BASE_IMAGE=infiniflow/ragflow:v0.27.2
FROM ${RAGFLOW_BASE_IMAGE}

USER root
WORKDIR /ragflow

COPY extensions/omnirag /ragflow/extensions/omnirag
COPY patches/omnirag /tmp/omnirag/patches
COPY scripts/omnirag/phase7_verify_runtime_source.py /tmp/omnirag/phase7_verify_runtime_source.py

RUN python /tmp/omnirag/phase7_verify_runtime_source.py /ragflow --mode prepatch \
 && patch -p1 < /tmp/omnirag/patches/phase2_adaptive_retrieval.patch \
 && patch -p1 < /tmp/omnirag/patches/phase3_multimodal_verifier.patch \
 && patch -p1 < /tmp/omnirag/patches/phase4_memory_agent_governance.patch \
 && patch -p1 < /tmp/omnirag/patches/phase5_tool_governance.patch \
 && python /tmp/omnirag/phase7_verify_runtime_source.py /ragflow --mode postpatch \
 && python -m compileall -q /ragflow/extensions/omnirag

LABEL org.opencontainers.image.title="OmniRAG-Agent"
LABEL org.opencontainers.image.description="RAGFlow v0.27.2 with OmniRAG phase2-5 governed extensions"
LABEL org.opencontainers.image.version="phase7-prelocal-v6"
