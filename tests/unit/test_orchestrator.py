from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from application.use_cases.orquestar_proceso import ProcesoOrchestrator
from infrastructure.llm.llm_service import LLMService


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.actualizar_resultado_detalle = AsyncMock()
    repo.insertar_error_detalle = AsyncMock()
    return repo


@pytest.fixture
def mock_llm():
    llm = LLMService()
    llm.analyze = AsyncMock(return_value={
        "explicacion": "test",
        "tokens_entrada": 10,
        "tokens_salida": 5,
        "provider": "test",
    })
    return llm


@pytest.fixture
def mock_mcp_omiso():
    with patch("application.use_cases.orquestar_proceso.MCPClient") as _, \
         patch("application.use_cases.orquestar_proceso.obtener_datos_fiscales") as odf:
        odf.return_value = {
            "nit": "9003189639",
            "razon_social": "TEST",
            "ciiu": "4711",
            "declaraciones_ica": [],
            "exogena_dian": [],
            "rues_estado": "",
        }
        yield


async def test_ejecutar_omiso(mock_mcp_omiso, mock_llm, mock_repo):
    orch = ProcesoOrchestrator(mock_llm, mock_repo)
    await orch.ejecutar(proceso_id="test-id", intento_id=1, nit="9003189639", detalle_id=42)
    mock_repo.actualizar_resultado_detalle.assert_awaited_once()


async def test_ejecutar_inexacto(mock_llm, mock_repo):
    with patch("application.use_cases.orquestar_proceso.MCPClient") as _, \
         patch("application.use_cases.orquestar_proceso.obtener_datos_fiscales") as odf:
        odf.return_value = {
            "nit": "9003189639",
            "razon_social": "TEST",
            "ciiu": "4711",
            "declaraciones_ica": [{"periodo": "2024-B1", "base_gravable": 50000000, "tarifa": 0.008, "impuesto": 400000}],
            "exogena_dian": [{"periodo": "2024", "ingresos": 120000000}],
            "rues_estado": "ACTIVO",
        }
        orch = ProcesoOrchestrator(mock_llm, mock_repo)
        await orch.ejecutar(proceso_id="test-id", intento_id=1, nit="9003189639", detalle_id=42)
        mock_repo.actualizar_resultado_detalle.assert_awaited_once()


async def test_ejecutar_error_mcp(mock_llm, mock_repo):
    with patch("application.use_cases.orquestar_proceso.MCPClient") as _, \
         patch("application.use_cases.orquestar_proceso.obtener_datos_fiscales") as odf:
        odf.side_effect = Exception("MCP connection error")
        orch = ProcesoOrchestrator(mock_llm, mock_repo)
        await orch.ejecutar(proceso_id="test-id", intento_id=1, nit="9003189639", detalle_id=42)
        mock_repo.insertar_error_detalle.assert_awaited_once()
