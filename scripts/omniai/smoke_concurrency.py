"""Verify that expensive jobs are bounded by the configured gate."""

import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from omniai_platform.resilience import AsyncConcurrencyGate


async def main() -> None:
    gate = AsyncConcurrencyGate(2)
    active = 0
    peak = 0

    async def work() -> None:
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.05)
        active -= 1

    started = time.monotonic()
    await asyncio.gather(*(gate.run(work) for _ in range(10)))
    elapsed = time.monotonic() - started
    assert peak == 2 and elapsed >= 0.2, (peak, elapsed)
    print(json.dumps({"submitted": 10, "limit": 2, "peak_active": peak, "elapsed_seconds": round(elapsed, 3)}))


if __name__ == "__main__":
    asyncio.run(main())
