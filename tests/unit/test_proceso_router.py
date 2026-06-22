import uuid
from unittest.mock import patch

from main import app
from fastapi.testclient import TestClient

client = TestClient(app)


@patch("routers.proceso.repo.obtener_cliente_por_nit")
@patch("routers.proceso.repo.crear_cliente")
@patch("routers.proceso.repo.obtener_proceso_por_criteria")
@patch("routers.proceso.repo.crear_proceso")
@patch("routers.proceso.repo.crear_intento")
@patch("routers.proceso.repo.actualizar_estado_proceso")
@patch("routers.proceso.repo.actualizar_estado_intento")
def test_crear_proceso_retorna_201(
    mock_estado_intento, mock_estado_proceso,
    mock_crear_intento, mock_crear_proceso,
    mock_obtener_criteria, mock_crear_cliente,
    mock_obtener_cliente,
):
    proc_id = uuid.uuid4()
    mock_obtener_cliente.return_value = {"id": uuid.uuid4(), "nit": "9003189639"}
    mock_obtener_criteria.return_value = None
    mock_crear_proceso.return_value = proc_id
    mock_crear_intento.return_value = 1

    response = client.post("/api/v1/proceso", json={
        "cliente_nit": "9003189639",
        "nombre": "Test proceso",
        "vigencia_ini": "2024-01-01",
        "vigencia_fin": "2024-12-31",
        "tipo_regimen": "COMUN",
        "actividades_economicas": ["4711", "5611"],
        "periodo": "2024",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["estado"] == "EN_COLA"
    assert "proceso_id" in data
