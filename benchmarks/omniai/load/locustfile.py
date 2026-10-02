from __future__ import annotations

from uuid import uuid4

from locust import HttpUser, between, task


class GatewayUser(HttpUser):
    wait_time = between(0.1, 0.8)

    @task(5)
    def health(self):
        self.client.get("/api/v1/health")

    @task(3)
    def overview(self):
        self.client.get("/api/v1/overview")

    @task(2)
    def incidents(self):
        self.client.get("/api/v1/incidents")

    @task(1)
    def submit_analysis(self):
        self.client.post(
            "/api/v1/analyses",
            json={"incident_id": "INC-20260922-001", "question": "分析 GW-01 异常"},
            headers={"Idempotency-Key": f"locust-{uuid4().hex}"},
        )
