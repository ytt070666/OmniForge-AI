"""Validation for the restricted OmniRAG TaskSpec."""

from __future__ import annotations

import math
import re
from collections import deque
from typing import Any

from .schema import (
    ALLOWED_STEP_KINDS,
    MAX_TASK_STEPS,
    RESERVED_STEP_IDS,
    SECRET_KEYS,
    STEP_OUTPUT_ALLOWLIST,
    STEP_PARAM_ALLOWLIST,
    TaskSpec,
)

_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
_REF_RE = re.compile(r"\$\{([^}]+)\}")
_SYS_REFS = {"sys.query", "sys.user_id", "sys.date", "sys.files", "sys.history", "sys.conversation_turns"}


class TaskSpecValidationError(ValueError):
    pass


def _walk(obj: Any, path: str = ""):
    if isinstance(obj, dict):
        for key, value in obj.items():
            p = f"{path}.{key}" if path else str(key)
            yield p, key, value
            yield from _walk(value, p)
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            p = f"{path}[{i}]"
            yield from _walk(value, p)


def _validate_no_inline_secret_fields(params: dict[str, Any], step_id: str) -> None:
    """Reject secret-like *fields*; do not claim secret-value detection."""

    for path, key, value in _walk(params):
        normalized = str(key).strip().lower()
        if normalized in SECRET_KEYS and value not in (None, "", [], {}):
            raise TaskSpecValidationError(
                f"step '{step_id}' embeds a secret-like field at '{path}'; use server-side configuration instead"
            )


def _finite_number(value: Any, field: str, step_id: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TaskSpecValidationError(f"step '{step_id}' {field} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise TaskSpecValidationError(f"step '{step_id}' {field} must be a finite number")
    return number


def _bounded_float(value: Any, field: str, step_id: str, low: float, high: float) -> None:
    number = _finite_number(value, field, step_id)
    if number < low or number > high:
        raise TaskSpecValidationError(f"step '{step_id}' {field} must be between {low} and {high}")


def _bounded_int(value: Any, field: str, step_id: str, low: int, high: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TaskSpecValidationError(f"step '{step_id}' {field} must be an integer")
    if value < low or value > high:
        raise TaskSpecValidationError(f"step '{step_id}' {field} must be between {low} and {high}")


def _validate_retrieval_params(step) -> None:
    p = step.params
    dataset_ids = p.get("dataset_ids", [])
    if not isinstance(dataset_ids, list) or not dataset_ids or not all(isinstance(x, str) and x.strip() for x in dataset_ids):
        raise TaskSpecValidationError(f"step '{step.id}' dataset_ids must be a non-empty array of non-empty strings")
    query = p.get("query", "${sys.query}")
    if not isinstance(query, str) or not query.strip():
        raise TaskSpecValidationError(f"step '{step.id}' query must be a non-empty string")
    if "similarity_threshold" in p:
        _bounded_float(p["similarity_threshold"], "similarity_threshold", step.id, 0.0, 1.0)
    if "keywords_similarity_weight" in p:
        _bounded_float(p["keywords_similarity_weight"], "keywords_similarity_weight", step.id, 0.0, 1.0)
    if "top_n" in p:
        _bounded_int(p["top_n"], "top_n", step.id, 1, 1024)
    if "rerank_candidates_count" in p:
        _bounded_int(p["rerank_candidates_count"], "rerank_candidates_count", step.id, 1, 4096)
    if "top_n" in p and "rerank_candidates_count" in p and p["rerank_candidates_count"] < p["top_n"]:
        raise TaskSpecValidationError(f"step '{step.id}' rerank_candidates_count must be >= top_n")
    if "rerank_id" in p and not isinstance(p["rerank_id"], str):
        raise TaskSpecValidationError(f"step '{step.id}' rerank_id must be a string")
    if "cross_languages" in p:
        value = p["cross_languages"]
        if not isinstance(value, list) or not all(isinstance(x, str) and x.strip() for x in value):
            raise TaskSpecValidationError(f"step '{step.id}' cross_languages must be an array of non-empty strings")
    for key in ("use_kg", "toc_enhance"):
        if key in p and not isinstance(p[key], bool):
            raise TaskSpecValidationError(f"step '{step.id}' {key} must be boolean")
    if "empty_response" in p and not isinstance(p["empty_response"], str):
        raise TaskSpecValidationError(f"step '{step.id}' empty_response must be a string")


def _validate_agent_params(step) -> None:
    p = step.params
    if not isinstance(p.get("llm_id"), str) or not p["llm_id"].strip():
        raise TaskSpecValidationError(f"step '{step.id}' requires a non-empty llm_id")
    for key in ("sys_prompt", "user_prompt", "description"):
        if key in p and not isinstance(p[key], str):
            raise TaskSpecValidationError(f"step '{step.id}' {key} must be a string")
    if "max_rounds" in p:
        _bounded_int(p["max_rounds"], "max_rounds", step.id, 0, 32)
    if "max_retries" in p:
        _bounded_int(p["max_retries"], "max_retries", step.id, 0, 10)
    if "temperature" in p:
        # RAGFlow's LLMParam.check_decimal_float constrains this to [0, 1].
        _bounded_float(p["temperature"], "temperature", step.id, 0.0, 1.0)
    if "cite" in p and not isinstance(p["cite"], bool):
        raise TaskSpecValidationError(f"step '{step.id}' cite must be boolean")


def _validate_message_params(step) -> None:
    p = step.params
    content = p.get("content")
    if isinstance(content, str):
        content = [content]
    if not isinstance(content, list) or not content or not all(isinstance(x, str) and x.strip() for x in content):
        raise TaskSpecValidationError(f"step '{step.id}' message content must be a non-empty string or string array")
    if "stream" in p and not isinstance(p["stream"], bool):
        raise TaskSpecValidationError(f"step '{step.id}' stream must be boolean")


def _validate_references(spec: TaskSpec, ids: set[str]) -> None:
    kind_by_id = {step.id: step.kind for step in spec.steps}
    for step in spec.steps:
        for _, _, value in _walk(step.params):
            if not isinstance(value, str):
                continue
            for raw in _REF_RE.findall(value):
                ref = raw.strip()
                if ref.startswith("sys."):
                    if ref not in _SYS_REFS:
                        raise TaskSpecValidationError(f"step '{step.id}' references unsupported system variable '${{{ref}}}'")
                    continue
                if "." not in ref:
                    raise TaskSpecValidationError(f"step '{step.id}' has malformed reference '${{{ref}}}'")
                step_ref, output = ref.split(".", 1)
                if step_ref not in ids:
                    raise TaskSpecValidationError(f"step '{step.id}' references unknown step '{step_ref}'")
                if step_ref not in set(step.depends_on):
                    raise TaskSpecValidationError(
                        f"step '{step.id}' references '{step_ref}' but does not declare it in depends_on; "
                        "TaskSpec v1 requires explicit data dependencies"
                    )
                if output not in STEP_OUTPUT_ALLOWLIST[kind_by_id[step_ref]]:
                    allowed = sorted(STEP_OUTPUT_ALLOWLIST[kind_by_id[step_ref]])
                    raise TaskSpecValidationError(
                        f"step '{step.id}' references unsupported output '${{{ref}}}'; allowed outputs for '{step_ref}' are {allowed}"
                    )


def _validate_acyclic(spec: TaskSpec, ids: set[str]) -> None:
    indegree = {sid: 0 for sid in ids}
    edges = {sid: [] for sid in ids}
    for step in spec.steps:
        for dep in step.depends_on:
            edges[dep].append(step.id)
            indegree[step.id] += 1
    queue = deque(sorted(sid for sid, degree in indegree.items() if degree == 0))
    visited = 0
    while queue:
        sid = queue.popleft()
        visited += 1
        for nxt in edges[sid]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)
    if visited != len(ids):
        raise TaskSpecValidationError("TaskSpec dependency graph contains a cycle")


def validate_taskspec(spec: TaskSpec) -> TaskSpec:
    if spec.version != "1.0":
        raise TaskSpecValidationError(f"unsupported TaskSpec version '{spec.version}'")
    if not spec.name.strip() or len(spec.name) > 128:
        raise TaskSpecValidationError("TaskSpec name must contain 1..128 characters")
    if len(spec.description) > 2000:
        raise TaskSpecValidationError("TaskSpec description must not exceed 2000 characters")
    if not spec.steps:
        raise TaskSpecValidationError("TaskSpec must contain at least one step")
    if len(spec.steps) > MAX_TASK_STEPS:
        raise TaskSpecValidationError(f"TaskSpec supports at most {MAX_TASK_STEPS} steps")

    ids: set[str] = set()
    for step in spec.steps:
        if not _ID_RE.fullmatch(step.id):
            raise TaskSpecValidationError(f"invalid step id '{step.id}'")
        if step.id in RESERVED_STEP_IDS:
            raise TaskSpecValidationError(f"step id '{step.id}' is reserved")
        if step.id in ids:
            raise TaskSpecValidationError(f"duplicate step id '{step.id}'")
        ids.add(step.id)
        if step.kind not in ALLOWED_STEP_KINDS:
            raise TaskSpecValidationError(f"unsupported step kind '{step.kind}'")
        unexpected = set(step.params) - STEP_PARAM_ALLOWLIST[step.kind]
        if unexpected:
            raise TaskSpecValidationError(f"step '{step.id}' has unsupported params: {sorted(unexpected)}")
        _validate_no_inline_secret_fields(step.params, step.id)

        if step.kind == "retrieval":
            _validate_retrieval_params(step)
        elif step.kind == "agent":
            _validate_agent_params(step)
        else:
            _validate_message_params(step)

    for step in spec.steps:
        if len(set(step.depends_on)) != len(step.depends_on):
            raise TaskSpecValidationError(f"step '{step.id}' has duplicate dependencies")
        for dep in step.depends_on:
            if dep not in ids:
                raise TaskSpecValidationError(f"step '{step.id}' depends on unknown step '{dep}'")
            if dep == step.id:
                raise TaskSpecValidationError(f"step '{step.id}' cannot depend on itself")

    _validate_acyclic(spec, ids)
    _validate_references(spec, ids)

    terminals = {step.id for step in spec.steps} - {dep for step in spec.steps for dep in step.depends_on}
    terminal_steps = [step for step in spec.steps if step.id in terminals]
    if not terminal_steps or any(step.kind != "message" for step in terminal_steps):
        raise TaskSpecValidationError("TaskSpec v1 requires every terminal step to be a message")
    return spec
