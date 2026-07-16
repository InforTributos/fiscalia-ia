import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from application.use_cases.orquestar_proceso import ProcesoOrchestrator
from infrastructure.llm.llm_service import LLMService


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.actualizar_resultado_detalle = AsyncMock()
    repo.insertar_error_detalle = AsyncMock()
    repo.actualizar_estado_detalle = AsyncMock()
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
    with patch("application.use_cases.orquestar_proceso.OracleClient") as _, \
         patch("application.use_cases.orquestar_proceso.obtener_datos_fiscales") as odf:
        odf.return_value = {
            "contribuyente_nit": "9003189639",
            "razon_social": "TEST",
            "ciiu": "4711",
            "declaraciones_ica": [],
            "exogena_dian": [],
            "rues_estado": "",
        }
        yield


async def test_ejecutar_omiso(mock_mcp_omiso, mock_llm, mock_repo):
    orch = ProcesoOrchestrator(mock_llm, mock_repo)
    await orch.ejecutar(proceso_id="test-id", intento_id=1, contribuyente_nit="9003189639", detalle_id=42, periodo="2024")
    mock_repo.actualizar_resultado_detalle.assert_awaited_once()


async def test_ejecutar_inexacto(mock_llm, mock_repo):
    with patch("application.use_cases.orquestar_proceso.OracleClient") as _, \
         patch("application.use_cases.orquestar_proceso.obtener_datos_fiscales") as odf:
        odf.return_value = {
            "contribuyente_nit": "9003189639",
            "razon_social": "TEST",
            "ciiu": "4711",
            "declaraciones_ica": [{"periodo": "2024-B1", "base_gravable": 50000000, "tarifa": 0.008, "impuesto": 400000}],
            "exogena_dian": [{"periodo": "2024", "ingresos": 120000000}],
            "rues_estado": "ACTIVO",
        }
        orch = ProcesoOrchestrator(mock_llm, mock_repo)
        await orch.ejecutar(proceso_id="test-id", intento_id=1, contribuyente_nit="9003189639", detalle_id=42, periodo="2024")
        mock_repo.actualizar_resultado_detalle.assert_awaited_once()


async def test_ejecutar_error_mcp(mock_llm, mock_repo):
    with patch("application.use_cases.orquestar_proceso.OracleClient") as _, \
         patch("application.use_cases.orquestar_proceso.obtener_datos_fiscales") as odf:
        odf.side_effect = Exception("MCP connection error")
        orch = ProcesoOrchestrator(mock_llm, mock_repo)
        pid_str = str(uuid.uuid4())
        await orch.ejecutar(proceso_id=pid_str, intento_id=1, contribuyente_nit="9003189639", detalle_id=42, periodo="2024")
        mock_repo.insertar_error_detalle.assert_awaited_once()


async def test_ejecutar_sin_datos_fiscales_escribe_mensaje(mock_llm, mock_repo):
    with patch("application.use_cases.orquestar_proceso.OracleClient") as _, \
         patch("application.use_cases.orquestar_proceso.obtener_datos_fiscales") as odf:
        odf.return_value = None
        orch = ProcesoOrchestrator(mock_llm, mock_repo)
        await orch.ejecutar(
            proceso_id="test-id", intento_id=1,
            contribuyente_nit="9003189639", detalle_id=42, periodo="2024",
        )
        mock_repo.actualizar_estado_detalle.assert_awaited_once_with(
            42, mensaje="Sin datos fiscales disponibles en Oracle para este NIT y periodo",
        )
        mock_repo.actualizar_resultado_detalle.assert_not_called()


async def test_ejecutar_con_datos_no_escribe_mensaje(mock_mcp_omiso, mock_llm, mock_repo):
    orch = ProcesoOrchestrator(mock_llm, mock_repo)
    await orch.ejecutar(
        proceso_id="test-id", intento_id=1,
        contribuyente_nit="9003189639", detalle_id=42, periodo="2024",
    )
    mock_repo.actualizar_estado_detalle.assert_not_called()
    mock_repo.actualizar_resultado_detalle.assert_awaited_once()
