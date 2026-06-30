from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


@patch("routers.analisis.LLMService")
@patch("routers.analisis.OracleClient")
@patch("routers.analisis.obtener_datos_fiscales")
def test_analisis_retorna_200(mock_pagination, mock_mcp_cls, mock_llm_cls):
    mock_mcp = AsyncMock()
    mock_mcp_cls.return_value = mock_mcp
    mock_pagination.return_value = {
        "nit": "9003189639",
        "razon_social": "COMERCIO XYZ S.A.S.",
        "ciiu": "4711",
        "regimen": "COMUN",
        "declaraciones_ica": [{"periodo": "2024-B1", "base_gravable": 50000000, "tarifa": 0.008, "impuesto": 400000}],
        "exogena_dian": [{"periodo": "2024", "ingresos": 120000000}],
        "rues_estado": "ACTIVO",
    }
    mock_llm = AsyncMock()
    mock_llm.analyze.return_value = {
        "explicacion": "Análisis simulado",
        "tokens_entrada": 100,
        "tokens_salida": 50,
        "provider": "test",
    }
    mock_llm_cls.return_value = mock_llm

    response = client.post("/api/v1/analizar/9003189639")
    assert response.status_code == 200
    data = response.json()
    assert data["nit"] == "9003189639"
    assert data["clasificacion"] == "INEXACTO"
    assert data["srf_total"] > 0


@patch("routers.analisis.OracleClient")
@patch("routers.analisis.obtener_datos_fiscales")
def test_analisis_404(mock_pagination, mock_mcp_cls):
    mock_mcp = AsyncMock()
    mock_mcp_cls.return_value = mock_mcp
    mock_pagination.return_value = None

    response = client.post("/api/v1/analizar/9999999999")
    assert response.status_code == 404
