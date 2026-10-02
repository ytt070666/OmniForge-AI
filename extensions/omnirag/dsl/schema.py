"""Restricted Phase-5 task specification schema.

The TaskSpec is intentionally smaller than RAGFlow's native Canvas DSL. It is a
safe authoring format that compiles *to* RAGFlow; it is not a second runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


ALLOWED_STEP_KINDS = {"retrieval", "agent", "message"}
RESERVED_STEP_IDS = {"begin"}
MAX_TASK_STEPS = 32
SECRET_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "authorization_token",
    "password",
    "secret",
    "token",
    "access_token",
    "refresh_token",
}

STEP_PARAM_ALLOWLIST = {
    "retrieval": {
        "dataset_ids",
        "query",
        "similarity_threshold",
        "keywords_similarity_weight",
        "top_n",
        "rerank_candidates_count",
        "rerank_id",
        "cross_languages",
        "use_kg",
        "toc_enhance",
        "empty_response",
    },
    "agent": {
        "llm_id",
        "sys_prompt",
        "user_prompt",
        "description",
        "max_rounds",
        "max_retries",
        "temperature",
        "cite",
    },
    "message": {"content", "stream"},
}

# Only outputs known to exist in the native RAGFlow components are exposed by
# TaskSpec v1. This blocks authoring references that would compile but fail at
# runtime (for example ``${retrieve.nonexistent}``).
STEP_OUTPUT_ALLOWLIST = {
    "retrieval": {"formalized_content"},
    "agent": {"content"},
    "message": {"content", "downloads"},
}


@dataclass(frozen=True)
class TaskStep:
    id: str
    kind: str
    depends_on: tuple[str, ...] = ()
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TaskSpec:
    version: str
    name: str
    description: str
    steps: tuple[TaskStep, ...]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "TaskSpec":
        """Parse without silently repairing malformed authoring input."""

        if not isinstance(value, dict):
            raise ValueError("TaskSpec must be a JSON object")
        unknown_top = set(value) - {"version", "name", "description", "steps"}
        if unknown_top:
            raise ValueError(f"TaskSpec has unsupported top-level fields: {sorted(unknown_top)}")
        if "version" in value and not isinstance(value["version"], str):
            raise ValueError("TaskSpec.version must be a string")
        if "name" in value and not isinstance(value["name"], str):
            raise ValueError("TaskSpec.name must be a string")
        raw_steps = value.get("steps")
        if not isinstance(raw_steps, list):
            raise ValueError("TaskSpec.steps must be an array")
        if len(raw_steps) > MAX_TASK_STEPS:
            raise ValueError(f"TaskSpec supports at most {MAX_TASK_STEPS} steps")

        steps: list[TaskStep] = []
        for index, item in enumerate(raw_steps):
            if not isinstance(item, dict):
                raise ValueError(f"TaskSpec.steps[{index}] must be an object")
            unknown_step = set(item) - {"id", "kind", "depends_on", "params"}
            if unknown_step:
                raise ValueError(f"TaskSpec.steps[{index}] has unsupported fields: {sorted(unknown_step)}")
            if not isinstance(item.get("id"), str):
                raise ValueError(f"TaskSpec.steps[{index}].id must be a string")
            if not isinstance(item.get("kind"), str):
                raise ValueError(f"TaskSpec.steps[{index}].kind must be a string")
            raw_depends = item.get("depends_on", [])
            if not isinstance(raw_depends, list) or not all(isinstance(x, str) for x in raw_depends):
                raise ValueError(f"TaskSpec.steps[{index}].depends_on must be an array of strings")
            raw_params = item.get("params", {})
            if not isinstance(raw_params, dict):
                raise ValueError(f"TaskSpec.steps[{index}].params must be an object")
            steps.append(
                TaskStep(
                    id=item.get("id") or "",
                    kind=item.get("kind") or "",
                    depends_on=tuple(raw_depends),
                    params=dict(raw_params),
                )
            )

        description = value.get("description", "")
        if not isinstance(description, str):
            raise ValueError("TaskSpec.description must be a string")
        return cls(
            version=value.get("version") or "1.0",
            name=value.get("name") or "",
            description=description,
            steps=tuple(steps),
        )
