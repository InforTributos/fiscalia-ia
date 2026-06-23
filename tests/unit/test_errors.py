from unittest.mock import patch

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


@patch("infrastructure.persistence.queries.obtener_proceso")
@patch("infrastructure.persistence.queries.listar_errores")
def test_errors_retorna_200(mock_errores, mock_proceso):
    mock_proceso.return_value = {"id": "550e8400-e29b-41d4-a716-446655440000", "estado": "ERROR"}
    mock_errores.return_value = (
        [
            {"id": 1, "intento_id": 1, "capa": "MCP", "codigo": "MCP_CONNECT_FAIL", "mensaje": "No se pudo conectar",
             "contexto": None, "created_at": None},
        ],
        [
            {"nit": "9003189639", "capa": "PROCESO", "codigo": "ANALISIS_FAIL", "mensaje": "Error en LLM",
             "contexto": None, "created_at": None},
        ],
    )

    response = client.get("/api/v1/proceso/550e8400-e29b-41d4-a716-446655440000/errors")
    assert response.status_code == 200
    data = response.json()
    assert data["proceso_id"] == "550e8400-e29b-41d4-a716-446655440000"
    assert len(data["errores_proceso"]) == 1
    assert len(data["errores_detalle"]) == 1
    assert data["total_errores_proceso"] == 1
    assert data["total_errores_detalle"] == 1


@patch("infrastructure.persistence.queries.obtener_proceso")
def test_errors_404(mock_proceso):
    mock_proceso.return_value = None
    response = client.get("/api/v1/proceso/550e8400-e29b-41d4-a716-446655440000/errors")
    assert response.status_code == 404


@patch("infrastructure.persistence.queries.obtener_proceso")
@patch("infrastructure.persistence.queries.listar_errores")
def test_errors_filtro_capa(mock_errores, mock_proceso):
    mock_proceso.return_value = {"id": "550e8400-e29b-41d4-a716-446655440000", "estado": "ERROR"}
    mock_errores.return_value = (
        [{"id": 1, "intento_id": 1, "capa": "MCP", "codigo": "MCP_CONNECT_FAIL", "mensaje": "No se pudo conectar",
          "contexto": None, "created_at": None}],
        [],
    )

    response = client.get("/api/v1/proceso/550e8400-e29b-41d4-a716-446655440000/errors?capa=MCP")
    assert response.status_code == 200
    assert response.json()["total_errores_proceso"] == 1
