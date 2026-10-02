"""Check NATS queue groups and JetStream ACK/redelivery on the local broker."""

from __future__ import annotations

import asyncio
import json
from uuid import uuid4

import nats


async def main() -> None:
    nc = await nats.connect("nats://127.0.0.1:4222")
    stream = f"OMNIAI_SMOKE_{uuid4().hex[:8].upper()}"
    try:
        counts = [0, 0]

        async def handle_one(_msg):
            counts[0] += 1

        async def handle_two(_msg):
            counts[1] += 1

        sub1 = await nc.subscribe("omniai.smoke.queue", queue="omniai-smoke", cb=handle_one)
        sub2 = await nc.subscribe("omniai.smoke.queue", queue="omniai-smoke", cb=handle_two)
        await nc.flush()
        for i in range(10):
            await nc.publish("omniai.smoke.queue", str(i).encode())
        await nc.flush()
        await asyncio.sleep(0.2)
        assert sum(counts) == 10 and min(counts) > 0, counts
        await sub1.unsubscribe()
        await sub2.unsubscribe()

        js = nc.jetstream()
        await js.add_stream(name=stream, subjects=[f"omniai.smoke.{stream.lower()}"])
        subject = f"omniai.smoke.{stream.lower()}"
        sub = await js.pull_subscribe(subject, durable=f"consumer_{stream.lower()}")
        await js.publish(subject, b"ack")
        first = (await sub.fetch(1, timeout=2))[0]
        assert first.data == b"ack"
        await first.ack()
        await js.publish(subject, b"retry")
        retry_first = (await sub.fetch(1, timeout=2))[0]
        await retry_first.nak(delay=0.1)
        retry_second = (await sub.fetch(1, timeout=3))[0]
        assert retry_second.data == b"retry"
        await retry_second.ack()
        print(json.dumps({"queue_group_deliveries": counts, "ack": "PASS", "retry_redelivery": "PASS"}))
    finally:
        try:
            await nc.jetstream().delete_stream(stream)
        except Exception:
            pass
        await nc.drain()


if __name__ == "__main__":
    asyncio.run(main())
