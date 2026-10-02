from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class GatewaySettings:
    host: str
    port: int
    max_concurrency: int
    agent_concurrency: int
    rate_limit_per_minute: int
    static_root: Path
    job_backend: str
    nats_url: str


def load_gateway_settings() -> GatewaySettings:
    return GatewaySettings(
        host=os.getenv("OMNIAI_GATEWAY_HOST", os.getenv("OMNIOPS_HOST", "127.0.0.1")),
        port=int(os.getenv("OMNIAI_GATEWAY_PORT", os.getenv("OMNIOPS_PORT", "8090"))),
        max_concurrency=max(1, int(os.getenv("OMNIAI_GATEWAY_CONCURRENCY", "64"))),
        agent_concurrency=max(1, int(os.getenv("OMNIAI_AGENT_CONCURRENCY", "4"))),
        rate_limit_per_minute=max(1, int(os.getenv("OMNIAI_RATE_LIMIT_PER_MINUTE", "240"))),
        static_root=ROOT / "apps" / "omniops" / "web",
        job_backend=os.getenv("OMNIAI_JOB_BACKEND", "local").strip().lower(),
        nats_url=os.getenv("OMNIAI_NATS_URL", "nats://127.0.0.1:4222"),
    )
