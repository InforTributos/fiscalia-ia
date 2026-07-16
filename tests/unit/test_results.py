from unittest.mock import patch

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


@patch("infrastructure.persistence.queries.obtener_proceso")
@patch("infrastructure.persistence.queries.listar_proceso_detalle")
def test_results_retorna_200(mock_listar, mock_proceso):
    mock_proceso.return_value = {"id": "550e8400-e29b-41d4-a716-446655440000", "estado": "COMPLETADO", "candidatos": 5}
    mock_listar.return_value = (2, [
        {
            "contribuyente_nit": "9003189639",
            "razon_social": "COMERCIO XYZ S.A.S.",
            "ciiu": "4711",
            "clasificacion": "INEXACTO",
            "mcp_score": 75.0,
            "mcp_razon": "Diferencia detectada",
            "srf_total": 45.5,
            "nivel_riesgo": "MEDIO",
            "hallazgos": [{"tipo": "SUBDECLARACION_EXOGENA", "diferencia": 70000000}],
            "explicacion_ia": "Análisis completo",
        },
        {
            "contribuyente_nit": "9003189640",
            "razon_social": "OTRO COMERCIO S.A.S.",
            "ciiu": "5611",
            "clasificacion": "OMISO",
            "mcp_score": 90.0,
            "mcp_razon": "Omisión total",
            "srf_total": 55.0,
            "nivel_riesgo": "ALTO",
            "hallazgos": [],
            "explicacion_ia": None,
        },
    ])

    response = client.get("/api/v1/proceso/550e8400-e29b-41d4-a716-446655440000/results")
    assert response.status_code == 200
    data = response.json()
    assert data["proceso_id"] == "550e8400-e29b-41d4-a716-446655440000"
    assert data["parcial"] is False
    assert data["paginacion"]["total_registros"] == 2
    assert len(data["resultados"]) == 2
    assert data["resultados"][0]["contribuyente_nit"] == "9003189639"


@patch("infrastructure.persistence.queries.obtener_proceso")
@patch("infrastructure.persistence.queries.listar_proceso_detalle")
def test_results_filtro_clasificacion(mock_listar, mock_proceso):
    mock_proceso.return_value = {"id": "550e8400-e29b-41d4-a716-446655440000", "estado": "COMPLETADO", "candidatos": 5}
    mock_listar.return_value = (1, [
        {
            "contribuyente_nit": "9003189640",
            "razon_social": "OTRO COMERCIO S.A.S.",
            "ciiu": "5611",
            "clasificacion": "OMISO",
            "mcp_score": 90.0,
            "mcp_razon": "Omisión total",
            "srf_total": 55.0,
            "nivel_riesgo": "ALTO",
            "hallazgos": [],
            "explicacion_ia": None,
        },
    ])

    response = client.get(
        "/api/v1/proceso/550e8400-e29b-41d4-a716-446655440000/results?clasificacion=OMISO",
    )
    assert response.status_code == 200
    assert response.json()["resultados"][0]["clasificacion"] == "OMISO"


@patch("infrastructure.persistence.queries.obtener_proceso")
def test_results_proceso_en_curso(mock_proceso):
    mock_proceso.return_value = {"id": "550e8400-e29b-41d4-a716-446655440000", "estado": "EN_PROCESO", "candidatos": 5}
    response = client.get("/api/v1/proceso/550e8400-e29b-41d4-a716-446655440000/results")
    assert response.status_code == 409


@patch("infrastructure.persistence.queries.obtener_proceso")
def test_results_404(mock_proceso):
    mock_proceso.return_value = None
    response = client.get("/api/v1/proceso/550e8400-e29b-41d4-a716-446655440000/results")
    assert response.status_code == 404
