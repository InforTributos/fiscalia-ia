"""
Locust Stress Tests — FiscalIA API
====================================
Escenarios de stress puro para medir límites del sistema.

Uso:
    # Rate limit saturation (50 users -> /analizar)
    locust -f tests/stress/locustfile_stress.py --host=http://localhost:8000 --headless -u 50 -r 10 --run-time 3m --csv=reports/stress_rate

    # Concurrent process creation (20 users -> POST /proceso)
    locust -f tests/stress/locustfile_stress.py --host=http://localhost:8000 --headless -u 20 -r 5 --run-time 3m --csv=reports/stress_proceso

    # Read-heavy (100 users -> health/status/results)
    locust -f tests/stress/locustfile_stress.py --host=http://localhost:8000 --headless -u 100 -r 20 --run-time 5m --csv=reports/stress_read

    # Mixed realistic (30 users -> mixed workload)
    locust -f tests/stress/locustfile_stress.py --host=http://localhost:8000 --headless -u 30 -r 5 --run-time 5m --csv=reports/stress_mixed
"""

import uuid

from locust import HttpUser, between, task

SEED_NITS = [
    "1065819988", "901501675", "901473230", "1065632021",
    "77195663", "1065858508", "1067810559", "15174506",
    "22581507", "900818892", "1051659301", "22587368",
]

PROCESO_PAYLOAD = {
    "entidad_nit": "800098911-8",
    "nombre": "Stress Test Proceso",
    "vigencia_ini": "2024-01-01",
    "vigencia_fin": "2024-12-31",
    "tipo_regimen": "COMUN",
    "actividades_economicas": ["4711", "4712"],
    "periodo": "2024",
}


def get_nit():
    import random
    return random.choice(SEED_NITS)


# ============================================================
# ESCENARIO 1: Rate Limit Saturation
# 50 usuarios → todos a /analizar (rate limit = 5/60s)
# Métrica: % de 429 vs 200
# ============================================================
class RateLimitSaturationUser(HttpUser):
    weight = 1
    wait_time = between(1, 3)

    @task
    def golpear_analizar(self):
        nit = get_nit()
        resp = self.client.post(f"/api/v1/analizar/{nit}?periodo=2024")
        if resp.status_code == 429:
            self.environment.events.request_success.fire(
                request_type="POST",
                name="/analizar (rate limited)",
                response_time=resp.elapsed.total_seconds() * 1000,
                response_length=len(resp.content),
            )
        elif resp.status_code in (200, 404):
            self.environment.events.request_success.fire(
                request_type="POST",
                name="/analizar (success)",
                response_time=resp.elapsed.total_seconds() * 1000,
                response_length=len(resp.content),
            )


# ============================================================
# ESCENARIO 2: Concurrent Process Creation
# 20 usuarios → todos a POST /proceso (rate limit = 10/60s)
# Métrica: 409s por duplicados, 429s por rate limit
# ============================================================
class ConcurrentProcessUser(HttpUser):
    weight = 1
    wait_time = between(2, 5)

    @task
    def crear_proceso(self):
        payload = dict(PROCESO_PAYLOAD)
        payload["nombre"] = f"Stress {uuid.uuid4().hex[:8]}"
        resp = self.client.post("/api/v1/proceso", json=payload)
        if resp.status_code == 409:
            self.environment.events.request_success.fire(
                request_type="POST",
                name="/proceso (duplicate)",
                response_time=resp.elapsed.total_seconds() * 1000,
                response_length=len(resp.content),
            )


# ============================================================
# ESCENARIO 3: Read-heavy Load
# 100 usuarios → solo GET endpoints
# Métrica: p95, p99 latencies
# ============================================================
class ReadHeavyUser(HttpUser):
    weight = 1
    wait_time = between(1, 2)

    @task(3)
    def health(self):
        self.client.get("/api/v1/health")

    @task(1)
    def status(self):
        self.client.get(
            "/api/v1/proceso/00000000-0000-0000-0000-000000000000/status",
            name="GET /proceso/{id}/status (404)",
        )

    @task(1)
    def resultados(self):
        self.client.get(
            "/api/v1/proceso/00000000-0000-0000-0000-000000000000/results?page=1&page_size=10",
            name="GET /proceso/{id}/results (404)",
        )

    @task(1)
    def listar_hallazgos(self):
        self.client.get("/api/v1/fiscalizacion/hallazgos?page=1&page_size=50")
