"""Optional NATS worker for distributed analysis requests.

The laptop profile does not require NATS. When enabled, this worker consumes
`omniai.analysis.requested` and publishes `omniai.analysis.completed` events.
"""
from __future__ import annotations

import asyncio
import json
import os
from uuid import uuid4

from .graph import build_graph
from .runtime import OmniAgentRuntime


async def main() -> None:
    try:
        import nats
    except ImportError as exc:
        raise SystemExit("Install nats-py from services/omniai_agent/requirements.txt") from exc

    url = os.getenv("OMNIAI_NATS_URL", "nats://127.0.0.1:4222")
    nc = await nats.connect(url)
    runtime = OmniAgentRuntime()
    graph = build_graph(classify=runtime.classify, retrieve=runtime.retrieve, tool=runtime.tool, generate=runtime.generate, verify=runtime.verify)

    async def handle(msg):
        try:
            event_in = json.loads(msg.data.decode("utf-8"))
            payload = event_in.get("payload") or {}
            run_id = str(payload["run_id"])
            state = {
                "incident_id": payload["incident_id"],
                "query": payload["query"],
                "retry_count": 0,
                "max_retries": int(payload.get("max_retries", 1)),
            }
            result = await asyncio.to_thread(graph.invoke, state)
            event = {"event_id": uuid4().hex, "event_type": "analysis.completed", "trace_id": event_in.get("trace_id", ""), "payload": {"run_id": run_id, "result": result}}
        except Exception as exc:
            event = {"event_id": uuid4().hex, "event_type": "analysis.failed", "trace_id": "", "payload": {"run_id": locals().get("run_id", ""), "error": f"{type(exc).__name__}: {exc}"}}
        subject = "omniai.analysis.completed" if event["event_type"] == "analysis.completed" else "omniai.analysis.failed"
        await nc.publish(subject, json.dumps(event, ensure_ascii=False).encode("utf-8"))

    await nc.subscribe("omniai.analysis.requested", queue="omniai-agent", cb=handle)
    print(f"OmniAI agent worker listening on {url}")
    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await nc.drain()


if __name__ == "__main__":
    asyncio.run(main())
