from unittest.mock import patch

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


@patch("infrastructure.persistence.queries.obtener_proceso")
@patch("infrastructure.persistence.queries.obtener_ultimo_intento")
@patch("infrastructure.persistence.queries.obtener_historial_intentos")
@patch("infrastructure.persistence.queries.obtener_entidad_por_id")
def test_status_retorna_200(mock_entidad, mock_historial, mock_ultimo, mock_proceso):
    mock_proceso.return_value = {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "estado": "COMPLETADO",
        "entidad_id": 1,
        "total_nits": 10,
        "candidatos": 5,
        "omisos": 3,
        "inexactos": 2,
    }
    mock_ultimo.return_value = {
        "numero_intento": 1,
        "estado": "COMPLETADO",
        "procesados": 5,
        "errores_count": 0,
        "started_at": None,
        "completed_at": None,
    }
    mock_historial.return_value = []
    mock_entidad.return_value = {"nit": "9003189639"}

    response = client.get("/api/v1/proceso/550e8400-e29b-41d4-a716-446655440000/status")
    assert response.status_code == 200
    data = response.json()
    assert data["proceso_id"] == "550e8400-e29b-41d4-a716-446655440000"
    assert data["estado"] == "COMPLETADO"
    assert "intento_actual" in data
    assert "progreso" in data


@patch("infrastructure.persistence.queries.obtener_proceso")
def test_status_404(mock_proceso):
    mock_proceso.return_value = None
    response = client.get("/api/v1/proceso/550e8400-e29b-41d4-a716-446655440000/status")
    assert response.status_code == 404
