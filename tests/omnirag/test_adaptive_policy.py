from __future__ import annotations

import os

from extensions.omnirag.retrieval.adaptive_policy import HeuristicPolicyV1
from extensions.omnirag.retrieval.integration import maybe_adapt_retrieval
from extensions.omnirag.retrieval.query_features import extract_query_features


def test_exact_identifier_is_lexical_heavy():
    d = HeuristicPolicyV1().decide(extract_query_features("Find identifier QX-741 exactly."))
    assert d.route == "lexical_precision"
    assert d.final_vector_weight < 0.4


def test_chinese_query_is_semantic_heavy():
    d = HeuristicPolicyV1().decide(extract_query_features("智能体的哪一种记忆用于保存过去的任务轨迹？"))
    assert d.route == "crosslingual_semantic"
    assert d.final_vector_weight > 0.7


def test_visual_query_requests_vision_route():
    d = HeuristicPolicyV1().decide(extract_query_features("Which server is highlighted in the topology diagram?"))
    assert d.requires_vision is True
    assert d.route == "visual_or_mixed"


def test_disabled_integration_preserves_final_weight(monkeypatch):
    monkeypatch.delenv("OMNIRAG_ADAPTIVE_RETRIEVAL", raising=False)
    d = maybe_adapt_retrieval("why does storage reduce peak load?", 0.3, 1024, 2048)
    assert d.enabled is False
    assert d.final_vector_weight == 0.3
    assert d.knn_top_k == 1024


def test_enabled_integration(monkeypatch):
    monkeypatch.setenv("OMNIRAG_ADAPTIVE_RETRIEVAL", "1")
    monkeypatch.setenv("OMNIRAG_ADAPTIVE_POLICY", "heuristic_v1")
    d = maybe_adapt_retrieval("What is the exact code QX-741?", 0.3, 1024, 2048)
    assert d.enabled is True
    assert d.policy == "heuristic_v1"
    assert d.final_vector_weight < 0.3
