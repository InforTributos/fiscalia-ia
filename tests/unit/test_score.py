import pytest
from unittest.mock import Mock, AsyncMock
from application.use_cases.calcular_score import CalcularScore


@pytest.mark.asyncio
async def test_calcular_score_retorna_componentes():
    mock_score = Mock()
    mock_score.obtener_srf.return_value = {
        "srf_total": 72, "comp_exogena": 30, "comp_tarifa": 22,
        "comp_omision": 15, "comp_rues": 5
    }
    mock_llm = Mock()
    mock_llm.analizar = AsyncMock(return_value={"explicacion": "Los principales factores..."})
    mock_cache = Mock()
    mock_cache.obtener.return_value = None

    use_case = CalcularScore(mock_score, mock_llm, mock_cache)
    resultado = await use_case.ejecutar("9003189639", "2025-01")

    assert resultado.srf == 72
    assert resultado.nivel == "ALTO"
    assert len(resultado.componentes) == 4


@pytest.mark.asyncio
async def test_score_bajo_retorna_nivel_bajo():
    mock_score = Mock()
    mock_score.obtener_srf.return_value = {
        "srf_total": 15, "comp_exogena": 5, "comp_tarifa": 5,
        "comp_omision": 3, "comp_rues": 2
    }
    mock_llm = Mock()
    mock_llm.analizar = AsyncMock(return_value={"explicacion": "Sin riesgo"})
    mock_cache = Mock()
    mock_cache.obtener.return_value = None

    use_case = CalcularScore(mock_score, mock_llm, mock_cache)
    resultado = await use_case.ejecutar("9003189639", "2025-01")

    assert resultado.nivel == "BAJO"
