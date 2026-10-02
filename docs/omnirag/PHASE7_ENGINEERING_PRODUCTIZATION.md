# Phase 7 — Engineering and Productization

## Scope
Phase 7 packages the already-reviewed OmniRAG extensions into reproducible deployment and CI artifacts. It does **not** claim that live Docker, Kubernetes, GPU, RAGFlow, or model inference has been validated in the current pre-local environment.

## Design rules
1. The official RAGFlow v0.27.2 source remains the frozen baseline in the delivery archive.
2. Docker image creation applies Phase 2→5 patches only after SHA-256 verification of the exact reviewed upstream files.
3. All OmniRAG feature flags default to off, preserving a reproducible baseline mode.
4. Kubernetes manifests use secret references; no real credentials are stored in Git.
5. Evaluation dashboards render `not_run` for absent live artifacts. They never manufacture metrics.
6. Phase 6 learned routing is not wired into production until its promotion gate passes on real inference.

## Deployment layers
- Local/research: upstream Docker Compose + `deploy/omnirag/docker/docker-compose.omnirag.yml`.
- Image: `deploy/omnirag/Dockerfile`, pinned to `infiniflow/ragflow:v0.27.2` by default.
- Kubernetes: minimal application-layer manifests under `deploy/omnirag/k8s/`. External MySQL/Redis/NATS/Elasticsearch/MinIO remain deployment dependencies and are intentionally not hidden inside this application manifest.
- CI: `.github/workflows/omnirag-ci.yml` runs deterministic contracts and an exact-source container build.

## Deliberate non-claims
The provided Kubernetes deployment is a conservative application skeleton, not a claim of production HA. HA requires external stateful services, persistent storage, ingress/TLS, autoscaling policy, backup/restore, model serving topology, and load testing in the target environment.
