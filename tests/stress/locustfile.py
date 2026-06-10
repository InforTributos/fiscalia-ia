from locust import HttpUser, between, task


class FiscalIAUser(HttpUser):
    wait_time = between(2, 5)

    @task
    def analizar_contribuyente(self):
        self.client.post(
            "/api/v1/analizar/9003189639",
            json={"periodo": "2025-01"},
            headers={"X-API-Key": "test-key"},
        )

    @task
    def consultar_score(self):
        self.client.post(
            "/api/v1/score/9003189639",
            json={"periodo": "2025-01"},
            headers={"X-API-Key": "test-key"},
        )

    @task
    def health_check(self):
        self.client.get("/api/v1/health")


# Ejecutar:
# locust -f tests/stress/locustfile.py --host=http://localhost:8000 --headless --users 100 --spawn-rate 10 --run-time 5m
