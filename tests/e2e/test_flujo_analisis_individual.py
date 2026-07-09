"""Tests E2E para POST /analizar/{nit}.

Cubre: Oracle fetch, SRF, LLM, cache hit/miss, errores NIT.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.e2e]

VALID_NIT = "9003189639"
DATOS_ORACLE = {
    "nit": VALID_NIT,
    "razon_social": "EMPRESA TEST E2E SAS",
    "ciiu": "4711",
    "regimen": "COMUN",
    "declaraciones_ica": [
        {"periodo": "2024", "base_gravable": 50000000, "impuesto": 3500000, "vlor_pago": 3500000},
    ],
    "exogena_dian": [
        {"periodo": "2024", "ingresos": 120000000},
    ],
    "rues_estado": "ACTIVO",
}


def test_analisis_individual_con_datos_oracle(client: TestClient):
    """Flujo completo: Oracle + SRF + LLM + respuesta 200."""
    with (
        patch("routers.analisis.obtener_datos_fiscales", return_value=DATOS_ORACLE),
        patch("routers.analisis.LLMService") as mock_llm_cls,
        patch("routers.analisis.get_cache") as mock_cache_cls,
    ):
        mock_llm = MagicMock()
        mock_llm.analyze = AsyncMock(return_value={
            "explicacion": "Analisis E2E simulado.",
            "provider": "mock",
        })
        mock_llm_cls.return_value = mock_llm

        mock_cache = MagicMock()
        mock_cache.obtener = MagicMock(return_value=None)
        mock_cache.guardar = MagicMock()
        mock_cache_cls.return_value = mock_cache

        resp = client.post(f"/api/v1/analizar/{VALID_NIT}?periodo=2024")

    assert resp.status_code == 200, f"Esperado 200, obtuvo {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["nit"] == VALID_NIT
    assert data["razon_social"] == "EMPRESA TEST E2E SAS"
    assert data["clasificacion"] in ("OMISO", "INEXACTO")
    assert data["srf_total"] >= 0
    assert data["nivel_riesgo"] in ("BAJO", "MEDIO", "ALTO")
    assert data["explicacion_ia"] == "Analisis E2E simulado."
    assert "componentes_srf" in data
    assert not data["cache_hit"]
    mock_llm.analyze.assert_awaited_once()


def test_analisis_individual_cache_hit(client: TestClient):
    """Cache hit retorna inmediato sin Oracle ni LLM."""
    with (
        patch("routers.analisis.obtener_datos_fiscales") as mock_oracle,
        patch("routers.analisis.get_cache") as mock_cache_cls,
    ):
        cached_response = {
            "nit": VALID_NIT,
            "razon_social": "CACHE E2E",
            "ciiu": "4711",
            "clasificacion": "OMISO",
            "mcp_score": 45.0,
            "mcp_razon": "",
            "srf_total": 45.0,
            "componentes_srf": [],
            "nivel_riesgo": "MEDIO",
            "hallazgos": [],
            "explicacion_ia": "Cache hit simulado.",
            "tokens_utilizados": 0,
            "duracion_ms": 0,
            "provider_utilizado": "cache",
            "cache_hit": True,
        }
        mock_cache = MagicMock()
        mock_cache.obtener = MagicMock(return_value=cached_response)
        mock_cache_cls.return_value = mock_cache

        resp = client.post(f"/api/v1/analizar/{VALID_NIT}?periodo=2024")

    assert resp.status_code == 200
    data = resp.json()
    assert data["cache_hit"]
    assert data["razon_social"] == "CACHE E2E"
    mock_oracle.assert_not_called()


def test_analisis_individual_nit_no_encontrado(client: TestClient):
    """NIT invalido → 404."""
    with patch("routers.analisis.obtener_datos_fiscales", return_value=None):
        resp = client.post("/api/v1/analizar/9999999999?periodo=2024")

    assert resp.status_code == 404


def test_analisis_individual_sin_nit(client: TestClient):
    """Falta NIT en path → 404."""
    resp = client.post("/api/v1/analizar/?periodo=2024")
    assert resp.status_code == 404
