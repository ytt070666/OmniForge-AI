from __future__ import annotations

from .store import Store, utcnow


def seed_demo(store: Store, reset: bool = False) -> None:
    if store.one("SELECT id FROM incidents LIMIT 1") and not reset:
        return
    if reset:
        store.clear_demo()
    now = utcnow()
    incidents = [
        {"id": "INC-20260922-001", "title": "GW-01 周期性 DNS 异常通信", "severity": "high", "status": "investigating", "asset_id": "GW-01", "summary": "IDS 在 14:03 后持续检测到周期性 DNS 查询与外联峰值。", "created_at": now, "updated_at": now},
        {"id": "INC-20260922-002", "title": "API Gateway P95 延迟升高", "severity": "medium", "status": "open", "asset_id": "API-GW-02", "summary": "P95 延迟在发布后由 180ms 上升到 620ms。", "created_at": now, "updated_at": now},
        {"id": "INC-20260922-003", "title": "季度补丁合规检查", "severity": "low", "status": "resolved", "asset_id": "SRV-GROUP-A", "summary": "核对服务器组补丁版本与升级 SOP。", "created_at": now, "updated_at": now},
    ]
    for row in incidents:
        store.insert("incidents", row)
    evidence = [
        {"id": "EV-001", "incident_id": "INC-20260922-001", "kind": "log", "title": "IDS DNS 告警", "source": "ids.log", "content": "GW-01 出现周期性 DNS 查询，持续以稳定间隔访问非常用外部域名；IDS 将该行为标记为 DNS beacon 异常。", "asset_url": "", "confidence": 0.94, "created_at": now},
        {"id": "EV-002", "incident_id": "INC-20260922-001", "kind": "image", "title": "网络拓扑", "source": "topology", "content": "网络拓扑显示 GW-01 通过网关连接外部网络，并确认 GW-01 是本次异常告警对应的边缘设备。", "asset_url": "/assets/01_network_topology.png", "confidence": 0.91, "created_at": now},
        {"id": "EV-003", "incident_id": "INC-20260922-001", "kind": "image", "title": "安全告警面板", "source": "security-dashboard", "content": "安全告警面板显示 GW-01 存在 DNS 异常，并伴随外联活动升高。", "asset_url": "/assets/05_security_dashboard.png", "confidence": 0.89, "created_at": now},
        {"id": "EV-004", "incident_id": "INC-20260922-001", "kind": "runbook", "title": "DNS Beacon 调查 Runbook", "source": "runbook-dns-beacon.md", "content": "DNS beacon 调查 Runbook 要求先核验资产身份、检查查询周期性与目标域名信誉，在证据确认后再评估网络隔离，不应在证据不足时直接执行破坏性处置。", "asset_url": "", "confidence": 0.86, "created_at": now},
        {"id": "EV-005", "incident_id": "INC-20260922-002", "kind": "image", "title": "P95 延迟曲线", "source": "latency-chart", "content": "P95 延迟在发布后明显升高，而错误率保持相对稳定。", "asset_url": "/assets/03_latency_chart.png", "confidence": 0.92, "created_at": now},
        {"id": "EV-006", "incident_id": "INC-20260922-002", "kind": "log", "title": "Deployment Timeline", "source": "deploy.log", "content": "API-GW-02 部署 2.8.4 版本后，P95 延迟在短时间内明显升高。", "asset_url": "", "confidence": 0.90, "created_at": now},
        {"id": "EV-007", "incident_id": "INC-20260922-003", "kind": "document", "title": "Patch SOP", "source": "patch-sop.pdf", "content": "补丁升级 SOP 要求依次完成快照、canary 灰度升级、健康检查、分阶段发布，并保持回滚条件。", "asset_url": "", "confidence": 0.98, "created_at": now},
    ]
    for row in evidence:
        store.insert("evidence", row)
    assets = [
        ("KB-001", "网络安全应急手册.pdf", "pdf", "ready", "demo", 1823040, ""),
        ("KB-002", "核心网络拓扑.png", "image", "ready", "demo", 283114, "apps/omniops/web/assets/01_network_topology.png"),
        ("KB-003", "DNS Beacon 调查 Runbook.md", "markdown", "ready", "demo", 18240, ""),
        ("KB-004", "API Gateway 运维手册.docx", "docx", "ready", "demo", 803214, ""),
        ("KB-005", "安全告警面板.png", "image", "ready", "demo", 310484, "apps/omniops/web/assets/05_security_dashboard.png"),
    ]
    for item in assets:
        store.insert("knowledge_assets", {"id": item[0], "name": item[1], "kind": item[2], "status": item[3], "source": item[4], "size_bytes": item[5], "local_path": item[6], "created_at": now})
    metrics = [
        ("retrieval_recall5", "Recall@5", "not_run", "not_run", "Retrieval"),
        ("retrieval_mrr", "MRR", "not_run", "not_run", "Retrieval"),
        ("multimodal_accuracy", "Multimodal accuracy", "not_run", "not_run", "Multimodal"),
        ("agent_task_success", "Agent task success", "not_run", "not_run", "Agent"),
        ("unsafe_tool_calls", "Unsafe tool execution", "0 / synthetic policy tests", "synthetic", "Tools"),
        ("router_json_valid", "Router JSON valid", "100% rule baseline", "synthetic", "Router"),
    ]
    for key, label, value, status, category in metrics:
        store.insert("evaluation_metrics", {"key": key, "label": label, "value": value, "status": status, "category": category, "updated_at": now})
