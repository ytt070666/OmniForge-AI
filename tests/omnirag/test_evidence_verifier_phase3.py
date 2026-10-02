from extensions.omnirag.verifier.evidence import EvidenceItem
from extensions.omnirag.verifier.evidence_graph import likely_conflict, split_claims, verify_claims


def test_split_claims():
    assert len(split_claims("A is 10. B is 20.")) == 2


def test_numeric_conflict_detection():
    assert likely_conflict("Recall is 91.3%", "Recall is 84.6%") is True


def test_supported_claim_passes():
    evidence = [
        EvidenceItem("e1", "table.png", "OmniRAG Multimodal Recall@5 is 91.3% and MRR is 0.87.", "table", 0.9),
        EvidenceItem("e2", "note.txt", "The experiment compares retrieval methods.", "text", 0.7),
    ]
    r = verify_claims("OmniRAG Multimodal Recall@5 is 91.3%.", evidence)
    assert r.claims[0].supported is True
    assert r.conflict_count == 0
    assert r.confidence > 0


def test_conflicting_number_abstains_or_requests_more():
    evidence = [EvidenceItem("e1", "table.png", "Hybrid RAG Recall@5 is 84.6%.", "table", 0.9)]
    r = verify_claims("Hybrid RAG Recall@5 is 91.3%.", evidence)
    assert r.claims[0].conflict is True
    assert r.decision == "abstain"


def test_multimodal_coverage_is_reported():
    evidence = [
        EvidenceItem("e1", "figure.png", "Sensor-B is the source device.", "image", 0.9),
        EvidenceItem("e2", "report.txt", "Sensor-B triggered DNS Tunneling.", "text", 0.8),
    ]
    r = verify_claims("Sensor-B is the source device and triggered DNS Tunneling.", evidence, support_threshold=0.2)
    assert r.modality_coverage > 0
