from pathlib import Path

from extensions.omnirag.multimodal.fusion import fuse_text_and_visual
from extensions.omnirag.multimodal.router import ModalityRouterV1
from extensions.omnirag.multimodal.types import VisualHit, VisualRecord
from extensions.omnirag.multimodal.visual_index import JsonlVisualIndex


def record(cid: str, vec, doc="doc"):
    return VisualRecord(
        chunk_id=cid,
        dataset_id="kb",
        document_id=doc,
        document_name=f"{doc}.png",
        image_id=f"kb-{cid}",
        content=f"content {cid}",
        vector=tuple(vec),
    )


def test_router_explicit_visual():
    d = ModalityRouterV1().decide("What value is shown in Figure 3 chart?")
    assert d.use_visual is True
    assert d.route == "visual_explicit"
    assert d.visual_weight > d.text_weight


def test_router_identifier_text_first(monkeypatch):
    monkeypatch.delenv("OMNIRAG_VISUAL_ALWAYS_ON", raising=False)
    d = ModalityRouterV1().decide("Find exact code QX-741")
    assert d.use_visual is False
    assert d.text_weight == 1.0


def test_visual_index_cosine_and_filters(tmp_path: Path):
    path = tmp_path / "visual.jsonl"
    idx = JsonlVisualIndex(path)
    idx.replace([record("a", [1, 0], "d1"), record("b", [0, 1], "d2"), record("c", [0.7, 0.7], "d3")])
    hits = idx.search([1, 0], top_k=3, dataset_ids={"kb"})
    assert [h.record.chunk_id for h in hits] == ["a", "c", "b"]
    filtered = idx.search([1, 0], top_k=3, document_ids={"d2"})
    assert [h.record.chunk_id for h in filtered] == ["b"]


def test_rrf_agreement_promotes_shared_candidate():
    d = ModalityRouterV1().decide("What does the image show?")
    text = [
        {"chunk_id": "shared", "similarity": 0.8, "content_with_weight": "shared"},
        {"chunk_id": "text-only", "similarity": 0.7, "content_with_weight": "text"},
    ]
    hits = [
        VisualHit(record("visual-only", [1, 0]), 0.95, 1),
        VisualHit(record("shared", [0.8, 0.2]), 0.90, 2),
    ]
    fused = fuse_text_and_visual(text, hits, d, top_n=4)
    by_id = {x.chunk_id: x for x in fused}
    assert by_id["shared"].agreement is True
    assert by_id["text-only"].agreement is False
    assert by_id["visual-only"].agreement is False
    assert fused[0].chunk_id == "shared"


def test_visual_only_candidate_has_ragflow_compatible_fields():
    d = ModalityRouterV1().decide("Read the chart")
    hit = VisualHit(record("v1", [1, 0], "d1"), 0.99, 1)
    fused = fuse_text_and_visual([], [hit], d, top_n=1)[0].chunk
    assert fused["chunk_id"] == "v1"
    assert fused["image_id"] == "kb-v1"
    assert fused["doc_id"] == "d1"
    assert fused["doc_type_kwd"] == "image"
    assert "omnirag_multimodal" in fused


def test_retrieved_image_data_uri_and_loading():
    import asyncio
    import base64
    from extensions.omnirag.multimodal.retrieved_images import load_retrieved_image_bytes, to_data_uri

    png = b"\x89PNG\r\n\x1a\n" + b"demo"
    calls = []
    def getter(*, bucket, fnm):
        calls.append((bucket, fnm))
        return png

    chunks = [
        {"image_id": "kb-chunk-1"},
        {"image_id": "kb-chunk-1"},
        {"image_id": "kb-chunk-2"},
    ]
    blobs = asyncio.run(load_retrieved_image_bytes(chunks, getter, max_images=2))
    assert blobs == [png, png]
    assert calls == [("kb", "chunk-1"), ("kb", "chunk-2")]
    uri = to_data_uri(png)
    assert uri.startswith("data:image/png;base64,")
    assert base64.b64decode(uri.split(",", 1)[1]) == png


def test_runtime_fusion_contract_adds_visual_doc_aggregation(tmp_path, monkeypatch):
    import asyncio
    import json
    from extensions.omnirag.multimodal.runtime import maybe_fuse_multimodal
    from extensions.omnirag.multimodal.visual_index import JsonlVisualIndex
    from extensions.omnirag.multimodal.types import VisualRecord

    index_path = tmp_path / "idx.jsonl"
    # Hash encoder query vector is deterministic but not semantically aligned to
    # image bytes. For this contract test we monkeypatch the runtime encoder.
    class Enc:
        def encode_texts(self, texts):
            return [[1.0, 0.0]]
    import extensions.omnirag.multimodal.runtime as rt
    monkeypatch.setattr(rt, "encoder_from_env", lambda: Enc())
    JsonlVisualIndex(index_path).replace([
        VisualRecord("v-only", "kb", "visual-doc", "visual.png", "kb-img", "visual fact", (1.0, 0.0)),
    ])
    monkeypatch.setenv("OMNIRAG_MULTIMODAL_RETRIEVAL", "1")
    monkeypatch.setenv("OMNIRAG_VISUAL_ALWAYS_ON", "1")
    monkeypatch.setenv("OMNIRAG_VISUAL_INDEX", str(index_path))
    kb = {"total": 1, "chunks": [{"chunk_id":"t1","doc_id":"text-doc","docnm_kwd":"text.txt","kb_id":"kb","similarity":0.8}], "doc_aggs":[{"doc_name":"text.txt","doc_id":"text-doc","count":1}]}
    out, meta = asyncio.run(maybe_fuse_multimodal("Explain the diagram", kb, ["kb"], None, 5))
    assert meta["used_visual"] is True
    assert any(x["doc_id"] == "visual-doc" for x in out["doc_aggs"])
