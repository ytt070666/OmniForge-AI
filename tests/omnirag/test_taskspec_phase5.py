import pytest

from extensions.omnirag.dsl import TaskSpec, TaskSpecValidationError, compile_taskspec, validate_taskspec


def valid_spec():
    return TaskSpec.from_dict(
        {
            "version": "1.0",
            "name": "grounded qa",
            "description": "retrieve then answer",
            "steps": [
                {
                    "id": "retrieve",
                    "kind": "retrieval",
                    "depends_on": [],
                    "params": {"dataset_ids": ["kb-1"], "query": "${sys.query}"},
                },
                {
                    "id": "answer",
                    "kind": "agent",
                    "depends_on": ["retrieve"],
                    "params": {
                        "llm_id": "qwen-test",
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
    )


def test_taskspec_compiles_to_native_ragflow_components_and_graph():
    out = compile_taskspec(valid_spec())
    assert set(out["components"]) == {"begin", "Retrieval:Omni_retrieve", "Agent:Omni_answer", "Message:Omni_respond"}
    assert out["components"]["Agent:Omni_answer"]["obj"]["params"]["prompts"][0]["content"].endswith("{Retrieval:Omni_retrieve@formalized_content}")
    assert out["components"]["Message:Omni_respond"]["obj"]["params"]["content"] == ["{Agent:Omni_answer@content}"]
    assert len(out["graph"]["nodes"]) == 4
    assert len(out["graph"]["edges"]) == 3


def test_taskspec_rejects_cycles():
    spec = TaskSpec.from_dict(
        {
            "version": "1.0",
            "name": "cycle",
            "steps": [
                {"id": "a", "kind": "agent", "depends_on": ["b"], "params": {"llm_id": "x"}},
                {"id": "b", "kind": "message", "depends_on": ["a"], "params": {"content": ["x"]}},
            ],
        }
    )
    with pytest.raises(TaskSpecValidationError, match="cycle"):
        validate_taskspec(spec)


def test_taskspec_rejects_inline_secret_fields():
    spec = TaskSpec.from_dict(
        {
            "version": "1.0",
            "name": "secret",
            "steps": [
                {"id": "answer", "kind": "agent", "params": {"llm_id": "x", "api_key": "secret"}},
                {"id": "respond", "kind": "message", "depends_on": ["answer"], "params": {"content": ["ok"]}},
            ],
        }
    )
    with pytest.raises(TaskSpecValidationError, match="unsupported params|secret"):
        validate_taskspec(spec)


def test_taskspec_rejects_unknown_reference():
    spec = TaskSpec.from_dict(
        {
            "version": "1.0",
            "name": "bad ref",
            "steps": [
                {"id": "answer", "kind": "agent", "params": {"llm_id": "x", "user_prompt": "${missing.content}"}},
                {"id": "respond", "kind": "message", "depends_on": ["answer"], "params": {"content": ["${answer.content}"]}},
            ],
        }
    )
    with pytest.raises(TaskSpecValidationError, match="unknown step"):
        validate_taskspec(spec)


def test_taskspec_requires_terminal_message():
    spec = TaskSpec.from_dict(
        {
            "version": "1.0",
            "name": "no terminal message",
            "steps": [{"id": "answer", "kind": "agent", "params": {"llm_id": "x"}}],
        }
    )
    with pytest.raises(TaskSpecValidationError, match="terminal step"):
        validate_taskspec(spec)


def test_taskspec_requires_reference_source_in_depends_on():
    spec = TaskSpec.from_dict(
        {
            "version": "1.0",
            "name": "implicit dependency",
            "steps": [
                {"id": "retrieve", "kind": "retrieval", "params": {"dataset_ids": ["kb-1"]}},
                {"id": "answer", "kind": "agent", "params": {"llm_id": "x", "user_prompt": "${retrieve.formalized_content}"}},
                {"id": "respond", "kind": "message", "depends_on": ["answer"], "params": {"content": ["${answer.content}"]}},
            ],
        }
    )
    with pytest.raises(TaskSpecValidationError, match="depends_on"):
        validate_taskspec(spec)


def test_taskspec_rejects_non_message_terminal_branch():
    spec = TaskSpec.from_dict(
        {
            "version": "1.0",
            "name": "orphan terminal",
            "steps": [
                {"id": "a", "kind": "agent", "params": {"llm_id": "x"}},
                {"id": "m", "kind": "message", "depends_on": ["a"], "params": {"content": ["${a.content}"]}},
                {"id": "orphan", "kind": "retrieval", "params": {"dataset_ids": ["kb-2"]}},
            ],
        }
    )
    with pytest.raises(TaskSpecValidationError, match="every terminal step"):
        validate_taskspec(spec)


def test_taskspec_parser_rejects_non_array_dependencies_instead_of_splitting_string():
    with pytest.raises(ValueError, match="depends_on"):
        TaskSpec.from_dict(
            {
                "version": "1.0",
                "name": "bad deps",
                "steps": [
                    {"id": "answer", "kind": "agent", "depends_on": "retrieve", "params": {"llm_id": "x"}}
                ],
            }
        )


def test_taskspec_rejects_unknown_output_reference():
    spec = TaskSpec.from_dict(
        {
            "version": "1.0",
            "name": "bad output",
            "steps": [
                {"id": "retrieve", "kind": "retrieval", "params": {"dataset_ids": ["kb-1"]}},
                {
                    "id": "answer",
                    "kind": "agent",
                    "depends_on": ["retrieve"],
                    "params": {"llm_id": "x", "user_prompt": "${retrieve.nonexistent}"},
                },
                {"id": "respond", "kind": "message", "depends_on": ["answer"], "params": {"content": ["${answer.content}"]}},
            ],
        }
    )
    with pytest.raises(TaskSpecValidationError, match="unsupported output"):
        validate_taskspec(spec)


def test_taskspec_rejects_invalid_parameter_types_and_bounds():
    spec = TaskSpec.from_dict(
        {
            "version": "1.0",
            "name": "bad types",
            "steps": [
                {
                    "id": "retrieve",
                    "kind": "retrieval",
                    "params": {"dataset_ids": ["kb-1"], "top_n": 0, "similarity_threshold": 1.5},
                },
                {"id": "respond", "kind": "message", "depends_on": ["retrieve"], "params": {"content": ["x"]}},
            ],
        }
    )
    with pytest.raises(TaskSpecValidationError, match="similarity_threshold|top_n"):
        validate_taskspec(spec)


def test_taskspec_compiler_uses_current_ragflow_rag_node_type():
    out = compile_taskspec(valid_spec())
    node = next(node for node in out["graph"]["nodes"] if node["id"] == "Retrieval:Omni_retrieve")
    assert node["type"] == "ragNode"


def test_taskspec_parser_rejects_unknown_authoring_fields():
    with pytest.raises(ValueError, match="unsupported top-level"):
        TaskSpec.from_dict({"version": "1.0", "name": "x", "steps": [], "tools": ["unsafe"]})
    with pytest.raises(ValueError, match="unsupported fields"):
        TaskSpec.from_dict(
            {
                "version": "1.0",
                "name": "x",
                "steps": [{"id": "m", "kind": "message", "params": {"content": ["x"]}, "execute": True}],
            }
        )
