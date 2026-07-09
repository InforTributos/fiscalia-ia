"""Tests E2E para manejo de errores HTTP.

Cubre: 404, 409, 422, 429, y health check.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.e2e]


def test_404_proceso_no_existe_status(client: TestClient):
    """GET /status con UUID valido pero no existente → 404."""
    from routers.status import repo as real_repo
    with patch.object(real_repo, "obtener_proceso", AsyncMock(return_value=None)):
        resp = client.get(f"/api/v1/proceso/{uuid.uuid4()}/status")
    assert resp.status_code == 404


def test_404_proceso_no_existe_results(client: TestClient):
    """GET /results con proceso inexistente → 404."""
    from routers.results import repo as real_repo
    with patch.object(real_repo, "obtener_proceso", AsyncMock(return_value=None)):
        resp = client.get(f"/api/v1/proceso/{uuid.uuid4()}/results")
    assert resp.status_code == 404


def test_404_proceso_no_existe_errors(client: TestClient):
    """GET /errors con proceso inexistente → 404."""
    from infrastructure.persistence import queries
    with patch.object(queries, "obtener_proceso", AsyncMock(return_value=None)):
        resp = client.get(f"/api/v1/proceso/{uuid.uuid4()}/errors")
    assert resp.status_code == 404


def test_409_proceso_duplicado_activo(client: TestClient, mock_router_repo):
    """POST /proceso con criterios repetidos → 409."""
    from routers.proceso import repo as real_repo

    with patch.object(real_repo, "obtener_proceso_por_criteria", AsyncMock(return_value={
        "id": uuid.uuid4(), "estado": "EN_PROCESO", "nombre": "Existente"
    })):
        resp = client.post("/api/v1/proceso", json={
            "cliente_nit": "9003189639", "nombre": "Duplicado",
            "vigencia_ini": "2024-01-01", "vigencia_fin": "2024-12-31",
            "tipo_regimen": "COMUN", "actividades_economicas": ["4711"], "periodo": "2024",
        })

    assert resp.status_code == 409


def test_422_campos_faltantes(client: TestClient):
    """POST /proceso sin campos obligatorios → 422."""
    resp = client.post("/api/v1/proceso", json={
        "nombre": "Incompleto",
    })
    assert resp.status_code == 422


def test_429_rate_limit_alcanzado(client: TestClient):
    """Excede limite de requests → 429."""
    from middleware.rate_limiter import RATE_LIMITS

    original = RATE_LIMITS.copy()
    RATE_LIMITS["/api/v1/health"] = (1, 60)

    try:
        client.get("/api/v1/health")
        resp = client.get("/api/v1/health")
        assert resp.status_code == 429
    finally:
        RATE_LIMITS.clear()
        RATE_LIMITS.update(original)


def test_health_ok(client: TestClient):
    """GET /health → 200 con checks."""
    with patch("routers.health.verificar_conexion", return_value=True):
        resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "checks" in data
