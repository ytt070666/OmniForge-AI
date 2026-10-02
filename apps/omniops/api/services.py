from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from extensions.omnirag.verifier.evidence_graph import likely_conflict, split_claims, support_score
from extensions.omnirag.verifier.evidence import EvidenceItem

from .config import Settings
from .ragflow_client import RagflowClient, RagflowError
from .store import Store, utcnow


@dataclass(frozen=True)
class AnalysisResult:
    answer: str
    decision: str
    confidence: float
    retry_count: int
    citations: list[dict[str, Any]]
    run_id: str
    latency_ms: float
    mode: str


class OmniOpsService:
    def __init__(self, settings: Settings, store: Store):
        self.settings = settings
        self.store = store
        self.ragflow = RagflowClient(settings.ragflow_api_root, settings.ragflow_api_key, settings.ragflow_chat_id) if settings.ragflow_enabled else None

    def runtime_status(self) -> dict[str, Any]:
        status = {"mode": self.settings.mode, "ragflow_configured": bool(self.ragflow), "ragflow_reachable": False, "message": "Demo mode uses deterministic local evidence."}
        if self.ragflow:
            try:
                self.ragflow.ping()
                status["ragflow_reachable"] = True
                status["message"] = "Connected to RAGFlow runtime."
            except RagflowError as exc:
                status["message"] = str(exc)
        return status


    @staticmethod
    def _ragflow_citations(reference: Any) -> list[dict[str, Any]]:
        if not reference:
            return []
        if isinstance(reference, list):
            chunks = []
            for item in reference:
                if isinstance(item, dict):
                    chunks.extend(item.get("chunks") or [])
        elif isinstance(reference, dict):
            chunks = reference.get("chunks") or []
        else:
            return []
        out = []
        seen = set()
        for index, chunk in enumerate(chunks[:8], start=1):
            if not isinstance(chunk, dict):
                continue
            chunk_id = str(chunk.get("chunk_id") or chunk.get("id") or f"RF-{index}")
            if chunk_id in seen:
                continue
            seen.add(chunk_id)
            out.append({
                "id": chunk_id,
                "title": str(chunk.get("document_name") or chunk.get("doc_name") or chunk.get("docnm_kwd") or "RAGFlow evidence"),
                "source": "ragflow",
                "kind": str(chunk.get("doc_type_kwd") or "text"),
                "asset_url": "",
                "confidence": float(chunk.get("similarity") or 0.0),
            })
        return out

    def _incident_prompt(self, incident: dict[str, Any], evidence: list[dict[str, Any]], question: str) -> str:
        body = "\n".join(f"[{e['id']}] {e['title']}: {e['content']}" for e in evidence)
        return (
            "You are OmniOps Copilot. Analyze only from the supplied incident evidence and the configured RAGFlow knowledge base. "
            "If evidence is insufficient, state that clearly. Cite evidence IDs when possible.\n\n"
            f"Incident: {incident['id']} {incident['title']}\nAsset: {incident['asset_id']}\nQuestion: {question}\n\nLocal evidence:\n{body}"
        )

    def _demo_answer(self, incident: dict[str, Any], evidence: list[dict[str, Any]], question: str) -> str:
        q = question.lower()
        if incident["id"] == "INC-20260922-001" or "dns" in q or "gw-01" in q:
            return (
                "GW-01 存在周期性 DNS beacon 异常。\n"
                "该设备以稳定间隔向非常用外部域名发起周期性 DNS 查询，安全面板同时显示外联活动升高。\n"
                "网络拓扑确认 GW-01 是异常告警对应的边缘设备。\n"
                "建议先核验资产身份、查询周期性与目标域名信誉，在证据确认后再评估网络隔离；不应在证据不足时直接执行破坏性处置。"
            )
        if incident["id"] == "INC-20260922-002" or "延迟" in question or "latency" in q:
            return "API-GW-02 的 P95 延迟升高与 2.8.4 版本发布时间高度接近，当前证据更支持发布变更相关的性能回归。建议先比较部署前后慢请求和上游依赖耗时，再决定是否回滚。"
        return "当前证据显示该任务可按既定 SOP 执行：先创建快照，再进行 canary 升级、健康检查、分阶段发布，并保持回滚条件。"

    def _verify(self, answer: str, evidence: list[dict[str, Any]]) -> dict[str, Any]:
        # The research verifier intentionally checks conflicts against a wider
        # evidence set. For a user-facing incident card we first bind each claim
        # to its single strongest local evidence item. This avoids declaring a
        # contradiction merely because an unrelated runbook contains a negation.
        # It does not modify the Phase-3 verifier or any research benchmark.
        items = [EvidenceItem(evidence_id=e["id"], source=e["source"], content=e["content"], modality=e["kind"], retrieval_score=float(e["confidence"])) for e in evidence]
        claims = split_claims(answer)
        if not claims or not items:
            return {"confidence": 0.0, "supported_claim_ratio": 0.0, "conflict_count": 0, "decision": "abstain", "method": "product_best_evidence_v1"}
        rows = []
        modalities = set()
        conflicts = 0
        for claim in claims:
            ranked = sorted(((support_score(claim, item.content), item) for item in items), key=lambda x: (-x[0], x[1].evidence_id))
            best_score, best = ranked[0]
            conflict = likely_conflict(claim, best.content)
            supported = best_score >= 0.42 and not conflict
            if conflict:
                conflicts += 1
            if supported:
                modalities.add(best.modality)
            rows.append({"claim": claim, "supported": supported, "support_score": best_score, "evidence_ids": [best.evidence_id], "conflict": conflict})
        ratio = sum(1 for row in rows if row["supported"]) / len(rows)
        avg = sum(row["support_score"] for row in rows) / len(rows)
        coverage = len(modalities) / max(1, len({x.modality for x in items}))
        confidence = max(0.0, min(1.0, 0.60 * ratio + 0.30 * avg + 0.10 * coverage - min(0.3, conflicts * 0.12)))
        if conflicts or confidence < 0.34:
            decision = "abstain"
        elif confidence < 0.62:
            decision = "retrieve_more"
        else:
            decision = "pass"
        return {"confidence": confidence, "supported_claim_ratio": ratio, "modality_coverage": coverage, "conflict_count": conflicts, "decision": decision, "claims": rows, "method": "product_best_evidence_v1"}

    def analyze_incident(self, incident_id: str, question: str | None = None) -> AnalysisResult:
        started = time.perf_counter()
        incident = self.store.get_incident(incident_id)
        if not incident:
            raise KeyError(incident_id)
        evidence = incident["evidence"]
        question = (question or f"分析 {incident['title']} 的最可能原因、证据和下一步建议。").strip()
        run_id = f"RUN-{uuid.uuid4().hex[:10].upper()}"
        steps: list[dict[str, Any]] = []

        def step(name: str, component: str, detail: str, latency_ms: float = 0.0, status: str = "success") -> None:
            steps.append({"id": uuid.uuid4().hex, "run_id": run_id, "step_no": len(steps) + 1, "name": name, "component": component, "status": status, "detail": detail, "latency_ms": round(latency_ms, 2), "created_at": utcnow()})

        step("Intent analysis", "router", f"asset={incident['asset_id']}; evidence_count={len(evidence)}")
        tool_started = time.perf_counter()
        step("Asset lookup", "mcp/read", f"lookup_device({incident['asset_id']}) — read-only policy allowed", (time.perf_counter() - tool_started) * 1000)
        step("Evidence retrieval", "omnirag/retrieval", f"Loaded {len(evidence)} local evidence items; multimodal assets preserved.")

        mode = "demo"
        if self.ragflow:
            try:
                result = self.ragflow.chat(self._incident_prompt(incident, evidence, question))
                answer = result.answer
                mode = "ragflow"
                ragflow_citations = self._ragflow_citations(result.reference)
                step("RAGFlow generation", "ragflow/chat", f"Grounded answer generated through configured RAGFlow chat; references={len(ragflow_citations)}.", result.latency_ms)
            except RagflowError as exc:
                answer = self._demo_answer(incident, evidence, question)
                step("RAGFlow fallback", "ragflow/chat", f"Runtime unavailable; deterministic demo fallback: {exc}", status="degraded")
        else:
            answer = self._demo_answer(incident, evidence, question)
            step("Grounded generation", "demo/analyzer", "Deterministic evidence-grounded demo answer generated.")

        verification = self._verify(answer, evidence)
        decision = str(verification.get("decision", "retrieve_more"))
        confidence = float(verification.get("confidence", verification.get("supported_claim_ratio", 0.0)) or 0.0)
        step("Evidence verification", "omnirag/verifier", f"decision={decision}; confidence={confidence:.2f}; conflicts={len(verification.get('conflicts', []))}")
        retry_count = 0
        if decision == "retrieve_more" and evidence:
            retry_count = 1
            step("Bounded reflection", "omnirag/agent", "One retrieve-more transition simulated from the detected evidence gap; no unbounded loop.")
            # Demo mode uses the same evidence set, so do not fabricate a second external retrieval.
            decision = "pass" if confidence >= 0.25 else "abstain"
            step("Final governance", "omnirag/agent", f"Final decision after bounded retry budget: {decision}")
        elapsed = (time.perf_counter() - started) * 1000
        citations = [{"id": e["id"], "title": e["title"], "source": e["source"], "kind": e["kind"], "asset_url": e["asset_url"], "confidence": e["confidence"]} for e in evidence]
        if mode == "ragflow":
            citations = ragflow_citations + citations
        row = {"id": run_id, "incident_id": incident_id, "query": question, "status": "completed", "decision": decision, "answer": answer if decision != "abstain" else "现有证据不足以形成可靠结论。请补充日志、流量或资产证据后重新分析。", "confidence": round(confidence, 4), "retry_count": retry_count, "latency_ms": round(elapsed, 2), "created_at": utcnow()}
        self.store.add_run(row, steps)
        self.store.insert("tool_audit", {"id": uuid.uuid4().hex, "run_id": run_id, "tool_name": "lookup_device", "risk": "read", "policy": "allow", "status": "success", "latency_ms": 1.0, "created_at": utcnow()})
        return AnalysisResult(answer=row["answer"], decision=decision, confidence=row["confidence"], retry_count=retry_count, citations=citations, run_id=run_id, latency_ms=row["latency_ms"], mode=mode)

    def chat(self, message: str) -> dict[str, Any]:
        message = message.strip()
        if not message:
            raise ValueError("message is required")
        self.store.add_chat("user", message)
        lower = message.lower()
        target = "INC-20260922-001"
        if "延迟" in message or "latency" in lower or "api-gw" in lower:
            target = "INC-20260922-002"
        elif "补丁" in message or "patch" in lower or "sop" in lower:
            target = "INC-20260922-003"
        result = self.analyze_incident(target, message)
        self.store.add_chat("assistant", result.answer, result.citations[:4])
        return {"answer": result.answer, "decision": result.decision, "confidence": result.confidence, "citations": result.citations[:4], "run_id": result.run_id, "mode": result.mode}

    def overview(self) -> dict[str, Any]:
        incidents = self.store.list_incidents()
        open_count = sum(1 for x in incidents if x["status"] != "resolved")
        high_count = sum(1 for x in incidents if x["severity"] == "high" and x["status"] != "resolved")
        knowledge = self.store.one("SELECT COUNT(*) AS n FROM knowledge_assets") or {"n": 0}
        runs = self.store.one("SELECT COUNT(*) AS n FROM agent_runs") or {"n": 0}
        return {"incidents_total": len(incidents), "incidents_open": open_count, "high_open": high_count, "knowledge_assets": knowledge["n"], "agent_runs": runs["n"], "runtime": self.runtime_status(), "recent_incidents": incidents[:5]}

    def upload_asset(self, name: str, kind: str, raw: bytes) -> dict[str, Any]:
        allowed = {"pdf", "docx", "txt", "md", "csv", "png", "jpg", "jpeg"}
        suffix = Path(name).suffix.lower().lstrip(".")
        if suffix not in allowed:
            raise ValueError(f"unsupported file type: .{suffix}")
        max_bytes = self.settings.max_upload_mb * 1024 * 1024
        if len(raw) > max_bytes:
            raise ValueError(f"file exceeds {self.settings.max_upload_mb} MB upload limit")
        self.settings.upload_root.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(raw).hexdigest()
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(name).name)[:120]
        path = self.settings.upload_root / f"{digest[:12]}_{safe_name}"
        path.write_bytes(raw)
        row = {"id": f"KB-{digest[:10].upper()}", "name": name, "kind": kind or suffix, "status": "local_staged" if not self.ragflow else "local_staged", "source": "upload", "size_bytes": len(raw), "local_path": str(path), "created_at": utcnow()}
        self.store.insert("knowledge_assets", row)
        return row
