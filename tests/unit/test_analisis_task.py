import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from tasks.analisis_task import analizar_proceso

VALID_UUID = str(uuid.uuid4())
CRITERIA = {"periodo": "2024", "tipo_regimen": "COMUN", "actividades_economicas": ["4711"]}


async def _agen(items):
    for item in items:
        yield item


async def _empty_agen():
    if False:
        yield  # pragma: no cover


def _config_oracle(mock_oc_cls):
    inst = MagicMock()
    inst.initialize = AsyncMock()
    inst.execute_sql = AsyncMock(return_value=[])
    inst.close = AsyncMock()
    mock_oc_cls.return_value = inst
    return inst


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.listar_proceso_detalle = AsyncMock()
    repo.actualizar_estado_proceso = AsyncMock()
    repo.actualizar_estado_intento = AsyncMock()
    repo.actualizar_progreso_intento = AsyncMock()
    repo.insertar_detalle = AsyncMock()
    repo.insertar_error_detalle = AsyncMock()
    repo.insertar_error_proceso = AsyncMock()
    return repo


@pytest.fixture
def mock_orch():
    orch = MagicMock()
    orch.ejecutar = AsyncMock()
    return orch


async def _passthrough(fn, *args, **kwargs):
    return await fn(*args, **kwargs)


@pytest.mark.asyncio
@patch("tasks.analisis_task.obtener_inexactos_retenciones")
@patch("tasks.analisis_task.obtener_inexactos_ciiu")
@patch("tasks.analisis_task.obtener_omisos_desconocidos")
@patch("tasks.analisis_task.obtener_omisos_conocidos")
@patch("tasks.analisis_task.OracleClient")
@patch("tasks.analisis_task.LLMService")
@patch("tasks.analisis_task.PostgresProcesoRepo")
@patch("tasks.analisis_task.ProcesoOrchestrator")
async def test_analizar_proceso_happy_path(
    mock_orch_cls, mock_repo_cls, mock_llm_cls,
    mock_oc,
    mock_omisos_con, mock_omisos_desc, mock_inex_ciiu, mock_inex_ret,
    mock_repo, mock_orch,
):
    mock_repo_cls.return_value = mock_repo
    mock_orch_cls.return_value = mock_orch
    mock_llm_cls.return_value = MagicMock()
    _config_oracle(mock_oc)

    mock_omisos_con.return_value = _agen([
        {"idntfccion": "9003189639", "nmbre_rzon_scial": "EMPRESA UNO", "id_actvdad_ecnmca": "4711"},
        {"idntfccion": "9003189640", "nmbre_rzon_scial": "EMPRESA DOS", "id_actvdad_ecnmca": "4721"},
    ])
    mock_omisos_desc.return_value = _empty_agen()
    mock_inex_ciiu.return_value = _agen([
        {"idntfccion": "9003189641", "nmbre_rzon_scial": "EMPRESA TRES", "id_actvdad_ecnmca": "5611"},
    ])
    mock_inex_ret.return_value = _empty_agen()

    mock_repo.listar_proceso_detalle.return_value = (3, [
        {"id": 1, "nit": "9003189639", "clasificacion": "OMISO"},
        {"id": 2, "nit": "9003189640", "clasificacion": "OMISO"},
        {"id": 3, "nit": "9003189641", "clasificacion": "INEXACTO"},
    ])
    mock_repo.bulk_insertar_detalle = AsyncMock(return_value=[1, 2, 3])

    await analizar_proceso(VALID_UUID, 1, CRITERIA)

    mock_repo.bulk_insertar_detalle.assert_awaited_once()
    bulk_calls = mock_repo.bulk_insertar_detalle.call_args[0][0]
    assert len(bulk_calls) == 3
    nits = [c["nit"] for c in bulk_calls]
    assert "9003189639" in nits
    assert "9003189640" in nits
    assert "9003189641" in nits

    mock_repo.actualizar_estado_proceso.assert_any_call(uuid.UUID(VALID_UUID), "PREFILTRANDO")
    mock_repo.actualizar_estado_proceso.assert_any_call(uuid.UUID(VALID_UUID), "PREFILTRADO_COMPLETADO")
    mock_repo.actualizar_estado_proceso.assert_any_call(uuid.UUID(VALID_UUID), "EN_PROCESO")
    mock_repo.actualizar_estado_proceso.assert_any_call(uuid.UUID(VALID_UUID), "COMPLETADO")

    assert mock_orch.ejecutar.call_count == 3
    mock_repo.actualizar_estado_intento.assert_called_with(1, "COMPLETADO")


@pytest.mark.asyncio
@patch("tasks.analisis_task.obtener_inexactos_retenciones")
@patch("tasks.analisis_task.obtener_inexactos_ciiu")
@patch("tasks.analisis_task.obtener_omisos_desconocidos")
@patch("tasks.analisis_task.obtener_omisos_conocidos")
@patch("tasks.analisis_task.OracleClient")
@patch("tasks.analisis_task.LLMService")
@patch("tasks.analisis_task.PostgresProcesoRepo")
@patch("tasks.analisis_task.ProcesoOrchestrator")
async def test_analizar_proceso_con_error_por_nit(
    mock_orch_cls, mock_repo_cls, mock_llm_cls,
    mock_oc,
    mock_omisos_con, mock_omisos_desc, mock_inex_ciiu, mock_inex_ret,
    mock_repo, mock_orch,
):
    mock_repo_cls.return_value = mock_repo
    mock_orch_cls.return_value = mock_orch
    mock_llm_cls.return_value = MagicMock()
    _config_oracle(mock_oc)

    mock_omisos_con.return_value = _agen([
        {"idntfccion": "9003189639", "nmbre_rzon_scial": "EMPRESA UNO"},
    ])
    mock_omisos_desc.return_value = _empty_agen()
    mock_inex_ciiu.return_value = _empty_agen()
    mock_inex_ret.return_value = _empty_agen()
    mock_repo.bulk_insertar_detalle = AsyncMock(return_value=[1])

    mock_orch.ejecutar.side_effect = Exception("LLM timeout")

    mock_repo.listar_proceso_detalle.return_value = (1, [
        {"id": 1, "nit": "9003189639", "clasificacion": "OMISO"},
    ])

    await analizar_proceso(VALID_UUID, 1, CRITERIA)

    mock_repo.insertar_error_detalle.assert_awaited_once()
    mock_repo.actualizar_estado_intento.assert_called_with(1, "ERROR")


@pytest.mark.asyncio
@patch("tasks.analisis_task.obtener_inexactos_retenciones")
@patch("tasks.analisis_task.obtener_inexactos_ciiu")
@patch("tasks.analisis_task.obtener_omisos_desconocidos")
@patch("tasks.analisis_task.obtener_omisos_conocidos")
@patch("tasks.analisis_task.OracleClient")
@patch("tasks.analisis_task.LLMService")
@patch("tasks.analisis_task.PostgresProcesoRepo")
@patch("tasks.analisis_task.ProcesoOrchestrator")
async def test_analizar_proceso_sin_candidatos(
    mock_orch_cls, mock_repo_cls, mock_llm_cls,
    mock_oc,
    mock_omisos_con, mock_omisos_desc, mock_inex_ciiu, mock_inex_ret,
    mock_repo, mock_orch,
):
    mock_repo_cls.return_value = mock_repo
    mock_orch_cls.return_value = mock_orch
    mock_llm_cls.return_value = MagicMock()
    _config_oracle(mock_oc)

    mock_omisos_con.return_value = _empty_agen()
    mock_omisos_desc.return_value = _empty_agen()
    mock_inex_ciiu.return_value = _empty_agen()
    mock_inex_ret.return_value = _empty_agen()

    await analizar_proceso(VALID_UUID, 1, CRITERIA)

    assert mock_orch.ejecutar.call_count == 0
    mock_repo.bulk_insertar_detalle.assert_not_called()
    mock_repo.actualizar_estado_proceso.assert_any_call(uuid.UUID(VALID_UUID), "COMPLETADO")
    mock_repo.actualizar_estado_intento.assert_called_with(1, "COMPLETADO")


@pytest.mark.asyncio
@patch("tasks.analisis_task.obtener_inexactos_retenciones")
@patch("tasks.analisis_task.obtener_inexactos_ciiu")
@patch("tasks.analisis_task.obtener_omisos_desconocidos")
@patch("tasks.analisis_task.obtener_omisos_conocidos")
@patch("tasks.analisis_task.OracleClient")
@patch("tasks.analisis_task.LLMService")
@patch("tasks.analisis_task.PostgresProcesoRepo")
@patch("tasks.analisis_task.ProcesoOrchestrator")
async def test_analizar_proceso_fallan_todos_generadores(
    mock_orch_cls, mock_repo_cls, mock_llm_cls,
    mock_oc,
    mock_omisos_con, mock_omisos_desc, mock_inex_ciiu, mock_inex_ret,
    mock_repo, mock_orch,
):
    mock_repo_cls.return_value = mock_repo
    mock_orch_cls.return_value = mock_orch
    mock_llm_cls.return_value = MagicMock()
    _config_oracle(mock_oc)

    mock_omisos_con.side_effect = Exception("Oracle timeout")
    mock_omisos_desc.side_effect = Exception("Query error")
    mock_inex_ciiu.side_effect = Exception("Lookup error")
    mock_inex_ret.side_effect = Exception("DB error")

    await analizar_proceso(VALID_UUID, 1, CRITERIA)

    assert mock_orch.ejecutar.call_count == 0
    mock_repo.actualizar_estado_intento.assert_called_with(1, "ERROR")
    mock_repo.actualizar_estado_proceso.assert_any_call(uuid.UUID(VALID_UUID), "ERROR")
    mock_repo.insertar_error_proceso.assert_called()


@pytest.mark.asyncio
@patch("tasks.analisis_task.obtener_inexactos_retenciones")
@patch("tasks.analisis_task.obtener_inexactos_ciiu")
@patch("tasks.analisis_task.obtener_omisos_desconocidos")
@patch("tasks.analisis_task.obtener_omisos_conocidos")
@patch("tasks.analisis_task.OracleClient")
@patch("tasks.analisis_task.LLMService")
@patch("tasks.analisis_task.PostgresProcesoRepo")
@patch("tasks.analisis_task.ProcesoOrchestrator")
async def test_analizar_proceso_ignora_nits_exactos(
    mock_orch_cls, mock_repo_cls, mock_llm_cls,
    mock_oc,
    mock_omisos_con, mock_omisos_desc, mock_inex_ciiu, mock_inex_ret,
    mock_repo, mock_orch,
):
    mock_repo_cls.return_value = mock_repo
    mock_orch_cls.return_value = mock_orch
    mock_llm_cls.return_value = MagicMock()
    _config_oracle(mock_oc)

    mock_omisos_con.return_value = _agen([
        {"idntfccion": "9003189639", "nmbre_rzon_scial": "EMPRESA UNO"},
    ])
    mock_omisos_desc.return_value = _empty_agen()
    mock_inex_ciiu.return_value = _empty_agen()
    mock_inex_ret.return_value = _empty_agen()
    mock_repo.bulk_insertar_detalle = AsyncMock(return_value=[1])

    mock_repo.listar_proceso_detalle.return_value = (3, [
        {"id": 1, "nit": "9003189639", "clasificacion": "EXACTO"},
        {"id": 2, "nit": "9012345678", "clasificacion": "OMISO"},
        {"id": 3, "nit": "9023456789", "clasificacion": "EXACTO"},
    ])

    await analizar_proceso(VALID_UUID, 1, CRITERIA)

    assert mock_orch.ejecutar.call_count == 1
    call_args = mock_orch.ejecutar.call_args
    assert call_args[0][2] == "9012345678"
