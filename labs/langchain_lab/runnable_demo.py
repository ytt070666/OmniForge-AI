from __future__ import annotations

import json

from langchain_core.runnables import RunnableLambda, RunnableParallel
from langchain_core.tools import tool


@tool
def calculate_availability(total_minutes: float, downtime_minutes: float) -> dict[str, float]:
    """Calculate service availability from total and downtime minutes."""
    if total_minutes <= 0 or downtime_minutes < 0 or downtime_minutes > total_minutes:
        raise ValueError("invalid minute values")
    availability = (total_minutes - downtime_minutes) / total_minutes
    return {"availability": availability, "availability_percent": availability * 100}


def normalize_query(value: dict) -> str:
    return str(value["query"]).strip().lower()


pipeline = RunnableParallel(
    normalized=RunnableLambda(normalize_query),
    metadata=RunnableLambda(lambda value: {"length": len(str(value["query"])), "framework": "langchain"}),
)


if __name__ == "__main__":
    print(json.dumps(pipeline.invoke({"query": "  Investigate GW-01 DNS anomaly  "}), indent=2, ensure_ascii=False))
    print(json.dumps(calculate_availability.invoke({"total_minutes": 1440, "downtime_minutes": 4}), indent=2))
