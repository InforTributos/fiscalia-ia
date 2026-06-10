import pytest
from unittest.mock import Mock, AsyncMock
from domain.value_objects.nit import NIT
from domain.value_objects.periodo import Periodo
from application.use_cases.analizar_contribuyente import AnalizarContribuyente


@pytest.mark.asyncio
async def test_analisis_con_subdeclaracion_retorna_hallazgo_alto():
    mock_cruce = Mock()
    mock_cruce.obtener_cruces.return_value = [
        {"ciiu": "4711", "ingreso_declarado": 50_000_000, "ingreso_exogena": 120_000_000,
         "diferencia": 70_000_000, "variacion_pct": 140, "umbral_superado": 1}
    ]
    mock_inc = Mock()
    mock_inc.obtener_inconsistencias.return_value = [
        {"tipo_incidencia": "SUBREGISTRO", "ciiu": "4711",
         "descripcion": "Subdeclaración detectada",
         "valor_declarado": 50_000_000, "valor_referencia": 120_000_000,
         "diferencia": 70_000_000, "severidad": "ALTA"}
    ]
    mock_score = Mock()
    mock_score.obtener_srf.return_value = {
        "srf_total": 85, "comp_exogena": 35, "comp_tarifa": 25,
        "comp_omision": 20, "comp_rues": 5
    }
    mock_analisis = Mock()
    mock_analisis.guardar_analisis.return_value = 1
    mock_llm = Mock()
    mock_llm.analizar = AsyncMock(return_value={
        "explicacion": "El contribuyente presenta una diferencia significativa...",
        "hallazgos_enriquecidos": [],
    })
    mock_cache = Mock()
    mock_cache.obtener.return_value = None

    use_case = AnalizarContribuyente(mock_cruce, mock_inc, mock_score, mock_analisis, mock_llm, mock_cache)
    resultado = await use_case.ejecutar("9003189639", "2025-01")

    assert resultado.score_riesgo > 70
    assert resultado.nivel_riesgo == "ALTO"
    assert len(resultado.hallazgos) == 1
    assert resultado.hallazgos[0]["tipo"] == "SUBREGISTRO"


@pytest.mark.asyncio
async def test_analisis_sin_hallazgos_retorna_bajo():
    mock_cruce = Mock()
    mock_cruce.obtener_cruces.return_value = []
    mock_inc = Mock()
    mock_inc.obtener_inconsistencias.return_value = []
    mock_score = Mock()
    mock_score.obtener_srf.return_value = {"srf_total": 15, "comp_exogena": 5, "comp_tarifa": 5, "comp_omision": 3, "comp_rues": 2}
    mock_analisis = Mock()
    mock_analisis.guardar_analisis.return_value = 1
    mock_llm = Mock()
    mock_llm.analizar = AsyncMock(return_value={"explicacion": "Sin hallazgos", "hallazgos_enriquecidos": []})
    mock_cache = Mock()
    mock_cache.obtener.return_value = None

    use_case = AnalizarContribuyente(mock_cruce, mock_inc, mock_score, mock_analisis, mock_llm, mock_cache)
    resultado = await use_case.ejecutar("9003189639", "2025-01")

    assert resultado.score_riesgo < 40
    assert resultado.nivel_riesgo == "BAJO"
    assert len(resultado.hallazgos) == 0
