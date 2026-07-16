"""Tests E2E para GET /status, /results, /errors.

Cubre: estado de proceso, resultados paginados, errores con filtros.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.e2e]

PID = uuid.uuid4()


def test_consultar_estado_proceso_existente(client: TestClient):
    """GET /status retorna estado con progreso."""
    from routers.status import repo as real_repo

    with (
        patch.object(real_repo, "obtener_proceso", AsyncMock(return_value={
            "id": PID, "estado": "EN_PROCESO", "entidad_id": uuid.uuid4(),
            "nombre": "Test", "criteria": "{}", "created_at": None,
            "total_nits": 10, "candidatos": 10, "omisos": 5, "inexactos": 5,
        })),
        patch.object(real_repo, "obtener_ultimo_intento", AsyncMock(return_value={
            "id": 1, "numero_intento": 1, "estado": "EN_PROCESO",
            "procesados": 5, "errores_count": 1, "started_at": None, "completed_at": None,
        })),
        patch.object(real_repo, "obtener_historial_intentos", AsyncMock(return_value=[])),
        patch.object(real_repo, "obtener_entidad_por_id", AsyncMock(return_value={
            "id": uuid.uuid4(), "nit": "9003189639",
        })),
    ):
        resp = client.get(f"/api/v1/proceso/{PID}/status")

    assert resp.status_code == 200
    data = resp.json()
    assert data["estado"] == "EN_PROCESO"
    assert "intento_actual" in data
    assert data["intento_actual"]["numero"] == 1
    assert "progreso" in data


def test_consultar_estado_proceso_no_existe(client: TestClient):
    """GET /status con proceso inexistente → 404."""
    from routers.status import repo as real_repo
    with patch.object(real_repo, "obtener_proceso", AsyncMock(return_value=None)):
        resp = client.get(f"/api/v1/proceso/{uuid.uuid4()}/status")
    assert resp.status_code == 404


def test_consultar_resultados_con_filtros(client: TestClient):
    """GET /results con paginacion y filtro de clasificacion."""
    from routers.results import repo as real_repo

    with (
        patch.object(real_repo, "obtener_proceso", AsyncMock(return_value={
            "id": PID, "estado": "COMPLETADO", "entidad_id": uuid.uuid4(),
        })),
        patch.object(real_repo, "listar_proceso_detalle", AsyncMock(return_value=(2, [
            {"id": 1, "nit": "9003189639", "razon_social": "EMPRESA UNO",
             "ciiu": "4711", "clasificacion": "OMISO", "mcp_score": 85.0,
             "srf_total": 85.0, "nivel_riesgo": "ALTO",
             "hallazgos": "[]", "explicacion_ia": "Test", "created_at": None},
            {"id": 2, "nit": "9012345678", "razon_social": "EMPRESA DOS",
             "ciiu": "5611", "clasificacion": "INEXACTO", "mcp_score": 45.0,
             "srf_total": 45.0, "nivel_riesgo": "MEDIO",
             "hallazgos": '[{"tipo":"TARIFA_INCORRECTA"}]', "explicacion_ia": "Test", "created_at": None},
        ]))),
    ):
        resp = client.get(f"/api/v1/proceso/{PID}/results?clasificacion=OMISO&page=1&page_size=10")

    assert resp.status_code == 200
    data = resp.json()
    assert data["paginacion"]["total_registros"] == 2
    assert len(data["resultados"]) == 2


def test_consultar_resultados_sin_terminar_rechaza(client: TestClient):
    """GET /results con proceso en curso y include_partial=false → 409."""
    from routers.results import repo as real_repo

    with patch.object(real_repo, "obtener_proceso", AsyncMock(return_value={
        "id": PID, "estado": "EN_PROCESO", "entidad_id": uuid.uuid4(),
    })):
        resp = client.get(f"/api/v1/proceso/{PID}/results")

    assert resp.status_code == 409


def test_consultar_errores_con_filtro_capa(client: TestClient):
    """GET /errors con filtro capa=MCP."""
    from infrastructure.persistence import queries

    with (
        patch.object(queries, "obtener_proceso", AsyncMock(return_value={"id": PID, "estado": "ERROR"})),
        patch.object(queries, "listar_errores", AsyncMock(return_value=(
            [{"id": 1, "intento_id": 1, "capa": "MCP", "codigo": "MCP_TIMEOUT",
              "mensaje": "Timeout", "contexto": None, "created_at": None}],
            [],
        ))),
    ):
        resp = client.get(f"/api/v1/proceso/{PID}/errors?capa=MCP")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total_errores_proceso"] == 1
    assert data["errores_proceso"][0]["capa"] == "MCP"
