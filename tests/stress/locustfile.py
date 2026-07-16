"""
Locust Load Tests — FiscalIA API
==================================
Escenarios de usuario realistas contra todos los endpoints.

Uso:
    locust -f tests/stress/locustfile.py --host=http://localhost:8000
    locust -f tests/stress/locustfile.py --host=http://localhost:8000 --headless -u 50 -r 5 --run-time 5m
"""

import json
import uuid

from locust import HttpUser, between, task

SEED_NITS = [
    "1065819988", "901501675", "901473230", "1065632021",
    "77195663", "1065858508", "1067810559", "15174506",
    "22581507", "900818892", "1051659301", "22587368",
]

PROCESO_PAYLOAD = {
    "entidad_nit": "800098911-8",
    "nombre": "Locust Test Proceso",
    "vigencia_ini": "2024-01-01",
    "vigencia_fin": "2024-12-31",
    "tipo_regimen": "COMUN",
    "actividades_economicas": ["4711", "4712"],
    "periodo": "2024",
}

CAMPANA_PAYLOAD = {
    "periodo": "2024",
    "nombre": "Locust Campana",
    "umbral_retenciones_pct": 5.0,
}


def get_nit():
    import random
    return random.choice(SEED_NITS)


class HealthUser(HttpUser):
    """Solo health check — baseline de latencia."""
    weight = 1
    wait_time = between(1, 3)

    @task
    def health(self):
        self.client.get("/api/v1/health")


class ProcesoUser(HttpUser):
    """Flujo completo de proceso: crear, status, results, errors."""
    weight = 3
    wait_time = between(3, 8)

    def on_start(self):
        self.proceso_id = None
        self.intento_id = None

    @task
    def crear_y_consultar_proceso(self):
        payload = dict(PROCESO_PAYLOAD)
        payload["nombre"] = f"Locust {uuid.uuid4().hex[:8]}"
        with self.client.post(
            "/api/v1/proceso", json=payload,
            name="POST /proceso",
            catch_response=True,
        ) as resp:
            if resp.status_code == 201:
                data = resp.json()
                self.proceso_id = data.get("proceso_id")
                self.intento_id = data.get("intento_id")
                resp.success()
            elif resp.status_code == 429:
                resp.success()
            else:
                resp.failure(f"Status {resp.status_code}")

        if self.proceso_id:
            self.client.get(
                f"/api/v1/proceso/{self.proceso_id}/status",
                name="GET /proceso/{id}/status",
            )
            self.client.get(
                f"/api/v1/proceso/{self.proceso_id}/results?include_partial=true",
                name="GET /proceso/{id}/results",
            )
            self.client.get(
                f"/api/v1/proceso/{self.proceso_id}/errors",
                name="GET /proceso/{id}/errors",
            )


class AnalisisUser(HttpUser):
    """Análisis individual de contribuyentes — endpoint más costoso."""
    weight = 5
    wait_time = between(5, 15)

    @task
    def analizar_nit(self):
        nit = get_nit()
        with self.client.post(
            f"/api/v1/analizar/{nit}?periodo=2024",
            name="POST /analizar/{nit}",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code in (404, 429):
                resp.success()
            else:
                resp.failure(f"Status {resp.status_code}")


class FiscalizacionUser(HttpUser):
    """CRUD de fiscalización: evaluar reglas, crear hallazgos, listar, revisar."""
    weight = 3
    wait_time = between(3, 10)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hallazgo_id = None

    @task
    def evaluar_reglas(self):
        nit = get_nit()
        with self.client.post(
            f"/api/v1/fiscalizacion/reglas/evaluar/{nit}?periodo=2024",
            name="POST /fiscalizacion/reglas/evaluar/{nit}",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 404, 422):
                resp.success()
            else:
                resp.failure(f"Status {resp.status_code}")

    @task
    def crear_y_listar_hallazgos(self):
        nit = get_nit()
        payload = {
            "nit": nit,
            "regla": "SUBDECLARACION",
            "periodo": "2024",
            "tipo_hallazgo": "SUBDECLARACION_ICA",
            "fuerza_probatoria": "MEDIA",
            "brecha_valor": 50000000.0,
            "impuesto_estimado": 7500000.0,
            "resumen": "Test desde Locust",
        }
        with self.client.post(
            "/api/v1/fiscalizacion/hallazgos", json=payload,
            name="POST /fiscalizacion/hallazgos",
            catch_response=True,
        ) as resp:
            if resp.status_code == 201:
                self.hallazgo_id = resp.json().get("id")
                resp.success()
            elif resp.status_code in (200, 422):
                resp.success()
            else:
                resp.failure(f"Status {resp.status_code}")

        self.client.get(
            "/api/v1/fiscalizacion/hallazgos?page=1&page_size=20",
            name="GET /fiscalizacion/hallazgos",
        )

        if self.hallazgo_id:
            self.client.get(
                f"/api/v1/fiscalizacion/hallazgos/{self.hallazgo_id}",
                name="GET /fiscalizacion/hallazgos/{id}",
            )


class BehavioralUser(HttpUser):
    """Análisis comportamental: comportamiento, grafo, expediente."""
    weight = 2
    wait_time = between(5, 15)

    @task
    def consultar_comportamiento(self):
        nit = get_nit()
        with self.client.get(
            f"/api/v1/contribuyente/{nit}/comportamiento?periodo=2024",
            name="GET /contribuyente/{nit}/comportamiento",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 404, 422):
                resp.success()
            else:
                resp.failure(f"Status {resp.status_code}")

    @task
    def consultar_grafo_riesgo(self):
        nit = get_nit()
        with self.client.get(
            f"/api/v1/contribuyente/{nit}/grafo-riesgo?periodo=2024",
            name="GET /contribuyente/{nit}/grafo-riesgo",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 404, 422):
                resp.success()
            else:
                resp.failure(f"Status {resp.status_code}")

    @task
    def consultar_expediente(self):
        nit = get_nit()
        with self.client.get(
            f"/api/v1/contribuyente/{nit}/expediente-fiscal?periodo=2024",
            name="GET /contribuyente/{nit}/expediente-fiscal",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 404, 422):
                resp.success()
            else:
                resp.failure(f"Status {resp.status_code}")

    @task
    def visor_grafo(self):
        nit = get_nit()
        self.client.get(
            f"/api/v1/visor/grafo/{nit}?periodo=2024",
            name="GET /visor/grafo/{nit}",
        )


class CampanaUser(HttpUser):
    """Creación de campañas de fiscalización."""
    weight = 1
    wait_time = between(5, 15)

    @task
    def crear_campana(self):
        payload = dict(CAMPANA_PAYLOAD)
        payload["nombre"] = f"Locust Campana {uuid.uuid4().hex[:8]}"
        with self.client.post(
            "/api/v1/campana", json=payload,
            name="POST /campana",
            catch_response=True,
        ) as resp:
            if resp.status_code == 201:
                resp.success()
            elif resp.status_code == 429:
                resp.success()
            else:
                resp.failure(f"Status {resp.status_code}")
