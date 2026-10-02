"""Prompt contract for a future LLM-to-TaskSpec adapter.

Phase 5 does not silently execute LLM-generated DSL. Generated JSON must pass
`validate_taskspec` and then compile to the native RAGFlow Canvas DSL.
"""

from __future__ import annotations

import json


def taskspec_generation_prompt(user_request: str, *, llm_id: str, dataset_ids: list[str] | None = None) -> str:
    example = {
        "version": "1.0",
        "name": "grounded_answer",
        "description": "Retrieve evidence and answer with one agent.",
        "steps": [
            {
                "id": "retrieve",
                "kind": "retrieval",
                "depends_on": [],
                "params": {"dataset_ids": dataset_ids or [], "query": "${sys.query}"},
            },
            {
                "id": "answer",
                "kind": "agent",
                "depends_on": ["retrieve"],
                "params": {
                    "llm_id": llm_id,
                    "sys_prompt": "Answer only from the supplied evidence.",
                    "user_prompt": "Question: ${sys.query}\nEvidence: ${retrieve.formalized_content}",
                },
            },
            {
                "id": "respond",
                "kind": "message",
                "depends_on": ["answer"],
                "params": {"content": ["${answer.content}"]},
            },
        ],
    }
    return (
        "Return exactly one JSON object matching OmniRAG TaskSpec v1.0. "
        "Allowed step kinds are retrieval, agent, and message. Do not include passwords, tokens, API keys, code execution, SQL execution, or arbitrary HTTP calls. "
        "All dependencies must form an acyclic graph, and at least one terminal step must be a message. "
        "Use ${sys.query} for the user query and ${step.output} for prior-step outputs.\n\n"
        f"User request:\n{user_request}\n\nExample:\n{json.dumps(example, ensure_ascii=False, indent=2)}"
    )
