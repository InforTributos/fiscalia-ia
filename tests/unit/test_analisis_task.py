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
        {"id": 1, "contribuyente_nit": "9003189639", "clasificacion": "OMISO"},
        {"id": 2, "contribuyente_nit": "9003189640", "clasificacion": "OMISO"},
        {"id": 3, "contribuyente_nit": "9003189641", "clasificacion": "INEXACTO"},
    ])
    mock_repo.bulk_insertar_detalle = AsyncMock(return_value=[1, 2, 3])

    await analizar_proceso(VALID_UUID, 1, CRITERIA)

    mock_repo.bulk_insertar_detalle.assert_awaited_once()
    bulk_calls = mock_repo.bulk_insertar_detalle.call_args[0][0]
    assert len(bulk_calls) == 3
    nits = [c["contribuyente_nit"] for c in bulk_calls]
    assert "9003189639" in nits
    assert "9003189640" in nits
    assert "9003189641" in nits

    from unittest.mock import call
    calls = mock_repo.actualizar_estado_proceso.call_args_list
    estados = [c[0][1] for c in calls]
    assert "PREFILTRANDO" in estados
    assert "PREFILTRADO_COMPLETADO" in estados
    assert "EN_PROCESO" in estados
    assert "COMPLETADO" in estados

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
        {"id": 1, "contribuyente_nit": "9003189639", "clasificacion": "OMISO"},
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
    estados = [c[0][1] for c in mock_repo.actualizar_estado_proceso.call_args_list]
    assert "COMPLETADO" in estados
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
    estados = [c[0][1] for c in mock_repo.actualizar_estado_proceso.call_args_list]
    assert "ERROR" in estados
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
        {"id": 1, "contribuyente_nit": "9003189639", "clasificacion": "EXACTO"},
        {"id": 2, "contribuyente_nit": "9012345678", "clasificacion": "OMISO"},
        {"id": 3, "contribuyente_nit": "9023456789", "clasificacion": "EXACTO"},
    ])

    await analizar_proceso(VALID_UUID, 1, CRITERIA)

    assert mock_orch.ejecutar.call_count == 1
    call_args = mock_orch.ejecutar.call_args
    assert call_args[0][2] == "9012345678"


CRITERIA_COMPLETO = {**CRITERIA, "tipo": "COMPLETO"}


@pytest.mark.asyncio
@patch("tasks.analisis_task._generar_resumen_proceso", new_callable=AsyncMock)
@patch("tasks.analisis_task._enriquecer_nit", new_callable=AsyncMock)
@patch("tasks.analisis_task._precargar_grupos", new_callable=AsyncMock)
@patch("tasks.analisis_task.obtener_inexactos_retenciones")
@patch("tasks.analisis_task.obtener_inexactos_ciiu")
@patch("tasks.analisis_task.obtener_omisos_desconocidos")
@patch("tasks.analisis_task.obtener_omisos_conocidos")
@patch("tasks.analisis_task.OracleClient")
@patch("tasks.analisis_task.LLMService")
@patch("tasks.analisis_task.PostgresProcesoRepo")
@patch("tasks.analisis_task.ProcesoOrchestrator")
async def test_analizar_proceso_completo_llama_enriquecimiento(
    mock_orch_cls, mock_repo_cls, mock_llm_cls,
    mock_oc,
    mock_omisos_con, mock_omisos_desc, mock_inex_ciiu, mock_inex_ret,
    mock_precargar, mock_enriquecer, mock_resumen,
    mock_repo, mock_orch,
):
    """tipo=COMPLETO debe llamar _enriquecer_nit y _generar_resumen_proceso"""
    mock_repo_cls.return_value = mock_repo
    mock_orch_cls.return_value = mock_orch
    mock_llm_cls.return_value = MagicMock()
    _config_oracle(mock_oc)

    mock_omisos_con.return_value = _agen([
        {"idntfccion": "9003189639", "nmbre_rzon_scial": "EMPRESA UNO", "id_actvdad_ecnmca": "4711"},
    ])
    mock_omisos_desc.return_value = _empty_agen()
    mock_inex_ciiu.return_value = _empty_agen()
    mock_inex_ret.return_value = _empty_agen()
    mock_repo.bulk_insertar_detalle = AsyncMock(return_value=[1])

    mock_precargar.return_value = {}
    mock_repo.listar_proceso_detalle.return_value = (1, [
        {"id": 1, "contribuyente_nit": "9003189639", "clasificacion": "OMISO", "ciiu": "4711"},
    ])

    await analizar_proceso(VALID_UUID, 1, CRITERIA_COMPLETO)

    mock_precargar.assert_awaited_once()
    mock_enriquecer.assert_awaited_once()
    mock_resumen.assert_awaited_once()
    assert mock_orch.ejecutar.call_count == 1


@pytest.mark.asyncio
@patch("tasks.analisis_task._generar_resumen_proceso", new_callable=AsyncMock)
@patch("tasks.analisis_task._enriquecer_nit", new_callable=AsyncMock)
@patch("tasks.analisis_task._precargar_grupos", new_callable=AsyncMock)
@patch("tasks.analisis_task.obtener_inexactos_retenciones")
@patch("tasks.analisis_task.obtener_inexactos_ciiu")
@patch("tasks.analisis_task.obtener_omisos_desconocidos")
@patch("tasks.analisis_task.obtener_omisos_conocidos")
@patch("tasks.analisis_task.OracleClient")
@patch("tasks.analisis_task.LLMService")
@patch("tasks.analisis_task.PostgresProcesoRepo")
@patch("tasks.analisis_task.ProcesoOrchestrator")
async def test_analizar_proceso_basico_no_llama_enriquecimiento(
    mock_orch_cls, mock_repo_cls, mock_llm_cls,
    mock_oc,
    mock_omisos_con, mock_omisos_desc, mock_inex_ciiu, mock_inex_ret,
    mock_precargar, mock_enriquecer, mock_resumen,
    mock_repo, mock_orch,
):
    """tipo=BASICO NO debe llamar _enriquecer_nit ni _generar_resumen_proceso"""
    mock_repo_cls.return_value = mock_repo
    mock_orch_cls.return_value = mock_orch
    mock_llm_cls.return_value = MagicMock()
    _config_oracle(mock_oc)

    mock_omisos_con.return_value = _agen([
        {"idntfccion": "9003189639", "nmbre_rzon_scial": "EMPRESA UNO", "id_actvdad_ecnmca": "4711"},
    ])
    mock_omisos_desc.return_value = _empty_agen()
    mock_inex_ciiu.return_value = _empty_agen()
    mock_inex_ret.return_value = _empty_agen()
    mock_repo.bulk_insertar_detalle = AsyncMock(return_value=[1])

    mock_precargar.return_value = {}
    mock_repo.listar_proceso_detalle.return_value = (1, [
        {"id": 1, "contribuyente_nit": "9003189639", "clasificacion": "OMISO", "ciiu": "4711"},
    ])

    await analizar_proceso(VALID_UUID, 1, CRITERIA)

    mock_precargar.assert_not_awaited()
    mock_enriquecer.assert_not_awaited()
    mock_resumen.assert_not_awaited()
    assert mock_orch.ejecutar.call_count == 1


# ── _enriquecer_nit: columna mensaje ──


@pytest.fixture
def mock_enriquecer_deps():
    """Mocks comunes para pruebas de _enriquecer_nit."""
    oc_inst = MagicMock()
    oc_inst.close = AsyncMock()
    oc_inst.initialize = AsyncMock()

    br_inst = MagicMock()
    br_inst.obtener_historico_nit = AsyncMock(return_value=[{"periodo": "2023", "base_gravable": 100000}])
    br_inst.obtener_pares = AsyncMock(return_value=[])

    with (
        patch("tasks.analisis_task.OracleClient", return_value=oc_inst),
        patch("tasks.analisis_task.OracleBehavioralRepository", return_value=br_inst),
        patch("tasks.analisis_task.obtener_datos_fiscales", new_callable=AsyncMock) as odf,
        patch("tasks.analisis_task.analizar_patrones_temporales", return_value=[]),
        patch("tasks.analisis_task._aplicar_reglas_fiscales", new_callable=AsyncMock, return_value=([], [])),
        patch("tasks.analisis_task._enriquecer_con_comportamiento", new_callable=AsyncMock, return_value=(None, [])),
        patch("tasks.analisis_task.calcular_score_fiscal_unificado", return_value={"score_fiscal_unificado": 0}),
        patch("tasks.analisis_task.queries.mergear_resultados_enriquecimiento", new_callable=AsyncMock),
        patch("tasks.analisis_task.queries.actualizar_estado_detalle", new_callable=AsyncMock) as aed,
    ):
        yield odf, aed, br_inst


@pytest.mark.asyncio
async def test_enriquecer_nit_sin_datos_fiscales_escribe_mensaje(mock_enriquecer_deps):
    odf, aed, br = mock_enriquecer_deps
    odf.return_value = None

    from tasks.analisis_task import _enriquecer_nit
    await _enriquecer_nit(42, "9003189639", "4711", "2024", {"4711": ([], "bench")}, "p123")

    aed.assert_awaited_once()
    assert aed.call_args[0] == (42,)
    assert "Sin datos fiscales disponibles en Oracle" in aed.call_args[1]["mensaje"]


@pytest.mark.asyncio
async def test_enriquecer_nit_sin_historial_escribe_mensaje(mock_enriquecer_deps):
    odf, aed, br = mock_enriquecer_deps
    odf.return_value = {"contribuyente_nit": "9003189639", "ciiu": "4711"}
    br.obtener_historico_nit.return_value = []

    with patch("domain.services.crosscheck_service.calcular_srf", return_value={"srf_total": 50}):
        from tasks.analisis_task import _enriquecer_nit
        await _enriquecer_nit(42, "9003189639", "4711", "2024", {"4711": ([], "bench")}, "p123")

    aed.assert_awaited_once()
    assert "Sin historial comportamental" in aed.call_args[1]["mensaje"]


@pytest.mark.asyncio
async def test_enriquecer_nit_ciiu_sin_grupo_escribe_mensaje(mock_enriquecer_deps):
    odf, aed, br = mock_enriquecer_deps
    odf.return_value = {"contribuyente_nit": "9003189639", "ciiu": "9999"}

    with patch("domain.services.crosscheck_service.calcular_srf", return_value={"srf_total": 50}):
        from tasks.analisis_task import _enriquecer_nit
        await _enriquecer_nit(42, "9003189639", "9999", "2024", {"4711": ([], "bench")}, "p123")

    aed.assert_awaited_once()
    assert "CIIU '9999' sin grupo de pares" in aed.call_args[1]["mensaje"]


@pytest.mark.asyncio
async def test_enriquecer_nit_multiples_razones(mock_enriquecer_deps):
    odf, aed, br = mock_enriquecer_deps
    odf.return_value = None
    br.obtener_historico_nit.return_value = []

    from tasks.analisis_task import _enriquecer_nit
    await _enriquecer_nit(42, "9003189639", "9999", "2024", {}, "p123")

    aed.assert_awaited_once()
    msg = aed.call_args[1]["mensaje"]
    assert "Sin datos fiscales disponibles en Oracle" in msg
    assert "Sin historial comportamental" in msg
    assert "CIIU '9999' sin grupo de pares" in msg


@pytest.mark.asyncio
async def test_enriquecer_nit_exception_escribe_mensaje(mock_enriquecer_deps):
    odf, aed, br = mock_enriquecer_deps
    odf.side_effect = Exception("Oracle connection lost")

    from tasks.analisis_task import _enriquecer_nit
    await _enriquecer_nit(42, "9003189639", "4711", "2024", {"4711": ([], "bench")}, "p123")

    aed.assert_awaited_once()
    assert "Error:" in aed.call_args[1]["mensaje"]
    assert "Oracle connection lost" in aed.call_args[1]["mensaje"]


@pytest.mark.asyncio
async def test_enriquecer_nit_happy_path_no_escribe_mensaje(mock_enriquecer_deps):
    odf, aed, br = mock_enriquecer_deps
    odf.return_value = {"contribuyente_nit": "9003189639", "ciiu": "4711"}

    with patch("domain.services.crosscheck_service.calcular_srf", return_value={"srf_total": 50}):
        from tasks.analisis_task import _enriquecer_nit
        await _enriquecer_nit(42, "9003189639", "4711", "2024", {"4711": ([], "bench")}, "p123")

    aed.assert_not_called()
