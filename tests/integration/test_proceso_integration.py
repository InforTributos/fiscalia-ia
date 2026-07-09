"""Tests de integración mockeados para el flujo POST /proceso.

Verifica el pipeline completo: endpoint HTTP, background task, pre-filtro de
candidatos, inserción en proceso_detalle, y análisis por orquestador.
Sin conexiones reales a infraestructura externa.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from main import app

pytestmark = [
    pytest.mark.integration,
]

VALID_PROCESO_ID = uuid.uuid4()
VALID_CLIENTE_NIT = "9003189639"

# =====================================================================
# Fixtures
# =====================================================================


@pytest.fixture(autouse=True)
def bypass_rate_limiter():
    """Desactiva rate limiting para tests HTTP.
    
    Ponemos el maximo de requests a un valor muy alto para que nunca se active.
    """
    from middleware import rate_limiter as rl
    original = rl.RATE_LIMITS.copy()
    for path in rl.RATE_LIMITS:
        max_req, window = rl.RATE_LIMITS[path]
        if max_req > 0:
            rl.RATE_LIMITS[path] = (999999, window)
    yield
    rl.RATE_LIMITS.clear()
    rl.RATE_LIMITS.update(original)


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def mock_router_repo():
    """Mockea métodos del repo a nivel de router (uno por uno, como test_proceso_router.py)."""
    from routers.proceso import repo as real_repo

    with (
        patch.object(real_repo, "obtener_cliente_por_nit", AsyncMock(return_value={"id": uuid.uuid4(), "nit": VALID_CLIENTE_NIT})),
        patch.object(real_repo, "obtener_proceso_por_criteria", AsyncMock(return_value=None)),
        patch.object(real_repo, "crear_proceso", AsyncMock(return_value=VALID_PROCESO_ID)),
        patch.object(real_repo, "crear_intento", AsyncMock(return_value=1)),
        patch.object(real_repo, "actualizar_estado_proceso", AsyncMock()),
        patch.object(real_repo, "actualizar_estado_intento", AsyncMock()),
    ):
        yield


async def _agen(items):
    for item in items:
        yield item


async def _empty_agen():
    if False:
        yield


# =====================================================================
# Test: HTTP endpoint lanza background task
# =====================================================================


def test_posta_proceso_retorna_201(client, mock_router_repo):
    """POST /proceso retorna 201 con estructura correcta."""
    response = post_proceso(client)
    assert response.status_code == 201
    data = response.json()
    assert data["estado"] == "EN_COLA"
    assert data["proceso_id"] == str(VALID_PROCESO_ID)
    assert data["intento_id"] == 1
    assert data["nombre"] == "Test proceso"
    assert data["cliente_nit"] == VALID_CLIENTE_NIT
    assert data["proceso_analisis"]["estado"] == "EN_COLA"
    assert "resumen" in data


def test_posta_proceso_lanza_background_task(client, mock_router_repo):
    """Verifica que POST /proceso lanza analizar_proceso con los argumentos correctos."""
    analizar_mock = MagicMock()

    with patch("routers.proceso.analizar_proceso", analizar_mock):
        post_proceso(client)

    analizar_mock.assert_called_once()
    args, kwargs = analizar_mock.call_args
    assert args[0] == str(VALID_PROCESO_ID)
    assert args[1] == 1
    assert args[2] == {
        "vigencia_ini": "2024-01-01",
        "vigencia_fin": "2024-12-31",
        "tipo_regimen": "COMUN",
        "actividades_economicas": ["4711", "5611"],
        "periodo": "2024",
    }


# =====================================================================
# Test: Creación de cliente automática
# =====================================================================


def test_posta_proceso_crea_cliente_si_no_existe(client):
    """Si el cliente no existe, lo crea automáticamente."""
    cliente_id_nuevo = uuid.uuid4()

    with (
        patch("routers.proceso.repo.obtener_cliente_por_nit", return_value=None),
        patch("routers.proceso.repo.crear_cliente", return_value=cliente_id_nuevo) as mock_crear,
        patch("routers.proceso.repo.obtener_proceso_por_criteria", return_value=None),
        patch("routers.proceso.repo.crear_proceso", return_value=VALID_PROCESO_ID),
        patch("routers.proceso.repo.crear_intento", return_value=1),
        patch("routers.proceso.repo.actualizar_estado_proceso"),
        patch("routers.proceso.repo.actualizar_estado_intento"),
        patch("routers.proceso.analizar_proceso"),
    ):
        response = post_proceso(client, nit_cliente="9999999999")

    assert response.status_code == 201
    mock_crear.assert_called_once_with("9999999999", "9999999999")


# =====================================================================
# Test: Prevención de duplicados
# =====================================================================


def test_posta_proceso_rechaza_duplicado_activo(client):
    """Mismos criterios + proceso activo → 409 Conflict."""
    proceso_existente = {
        "id": uuid.uuid4(),
        "estado": "EN_PROCESO",
        "nombre": "Existente",
    }

    with (
        patch("routers.proceso.repo.obtener_cliente_por_nit", return_value={"id": uuid.uuid4(), "nit": VALID_CLIENTE_NIT}),
        patch("routers.proceso.repo.obtener_proceso_por_criteria", return_value=proceso_existente),
        patch("routers.proceso.analizar_proceso"),
    ):
        response = post_proceso(client)

    assert response.status_code == 409


@pytest.mark.parametrize("estado_activo", ["PENDIENTE", "EN_COLA", "PREFILTRANDO"])
def test_posta_proceso_rechaza_estados_activos(client, estado_activo):
    """Cualquier estado activo → 409."""
    proceso_existente = {"id": uuid.uuid4(), "estado": estado_activo, "nombre": "Existente"}

    with (
        patch("routers.proceso.repo.obtener_cliente_por_nit", return_value={"id": uuid.uuid4(), "nit": VALID_CLIENTE_NIT}),
        patch("routers.proceso.repo.obtener_proceso_por_criteria", return_value=proceso_existente),
        patch("routers.proceso.analizar_proceso"),
    ):
        response = post_proceso(client)

    assert response.status_code == 409


# =====================================================================
# Test: Reintento sobre proceso completado/error
# =====================================================================


@pytest.mark.parametrize("estado_previo", ["COMPLETADO", "ERROR", "INTERRUMPIDO"])
def test_posta_proceso_reintento_con_nuevo_intento(client, estado_previo):
    """Proceso completado/error → nuevo intento (no 409)."""
    proceso_existente = {
        "id": uuid.uuid4(),
        "estado": estado_previo,
        "intentos_total": 1,
    }

    with (
        patch("routers.proceso.repo.obtener_cliente_por_nit", return_value={"id": uuid.uuid4(), "nit": VALID_CLIENTE_NIT}),
        patch("routers.proceso.repo.obtener_proceso_por_criteria", return_value=proceso_existente),
        patch("routers.proceso.repo.crear_proceso", return_value=VALID_PROCESO_ID),
        patch("routers.proceso.repo.crear_intento", return_value=2) as mock_intento,
        patch("routers.proceso.repo.actualizar_estado_proceso"),
        patch("routers.proceso.repo.actualizar_estado_intento"),
        patch("routers.proceso.analizar_proceso"),
    ):
        response = post_proceso(client)

    assert response.status_code == 201
    assert response.json()["intento_id"] == 2
    mock_intento.assert_called_once()
    assert mock_intento.call_args[0][1] == 2


# =====================================================================
# Test: Validación de esquema
# =====================================================================


@pytest.mark.parametrize("missing_field", [
    "cliente_nit", "nombre", "vigencia_ini", "vigencia_fin",
    "tipo_regimen", "actividades_economicas", "periodo",
])
def test_posta_proceso_requiere_campos_obligatorios(client, missing_field):
    """Campos obligatorios faltantes → 422."""
    payload = {
        "cliente_nit": "9003189639",
        "nombre": "Test",
        "vigencia_ini": "2024-01-01",
        "vigencia_fin": "2024-12-31",
        "tipo_regimen": "COMUN",
        "actividades_economicas": ["4711"],
        "periodo": "2024",
    }
    del payload[missing_field]

    with patch("routers.proceso.analizar_proceso"):
        response = client.post("/api/v1/proceso", json=payload)

    assert response.status_code == 422


# =====================================================================
# Test: Flujo completo con infraestructura mockeada
# =====================================================================


@pytest.mark.asyncio
async def test_flujo_completo_con_candidatos_mixtos():
    """Verifica el flujo completo: pre-filtro → inserción → análisis."""
    from tasks.analisis_task import analizar_proceso

    mock_repo = MagicMock()
    mock_repo.actualizar_estado_proceso = AsyncMock()
    mock_repo.actualizar_estado_intento = AsyncMock()
    mock_repo.insertar_detalle = AsyncMock()
    mock_repo.insertar_error_proceso = AsyncMock()
    mock_repo.insertar_error_detalle = AsyncMock()
    mock_repo.actualizar_progreso_intento = AsyncMock()
    mock_repo.listar_proceso_detalle = AsyncMock(return_value=(2, [
        {"id": 1, "nit": "9003189639", "clasificacion": "OMISO"},
        {"id": 2, "nit": "9012345678", "clasificacion": "INEXACTO"},
    ]))

    mock_orch = MagicMock()
    mock_orch.ejecutar = AsyncMock()

    mock_oc = MagicMock()
    mock_oc.initialize = AsyncMock()
    mock_oc.execute_sql = AsyncMock(return_value=[])

    mock_lookup = MagicMock()
    mock_lookup.get_impuesto_id = AsyncMock(return_value=101)
    mock_lookup.get_programa_id = AsyncMock(return_value=201)
    mock_lookup.get_configuracion_declaracion = AsyncMock(
        return_value=MagicMock(ind_prsntcion_dclrcion="A")
    )
    mock_lookup.get_atributos_ica = AsyncMock(return_value=MagicMock(
        ciiu_ids=[5125], tarifa_ids=[2107],
        ret_recibidas_ids=[2135], ret_practicadas_ids=[2136],
    ))

    proceso_id = str(uuid.uuid4())
    criteria = {"periodo": "2024", "tipo_regimen": "COMUN", "actividades_economicas": ["4711"]}

    with (
        patch("tasks.analisis_task.PostgresProcesoRepo", return_value=mock_repo),
        patch("tasks.analisis_task.ProcesoOrchestrator", return_value=mock_orch),
        patch("tasks.analisis_task.LLMService", return_value=MagicMock()),
        patch("tasks.analisis_task.OracleClient", return_value=mock_oc),
        patch("tasks.analisis_task.RepositorioLookupOracle", return_value=mock_lookup),
        patch("tasks.analisis_task.obtener_omisos_conocidos",
              return_value=_agen([{"idntfccion": "9003189639", "nmbre_rzon_scial": "EMPRESA UNO",
                                   "id_actvdad_ecnmca": "4711"}])),
        patch("tasks.analisis_task.obtener_omisos_desconocidos", return_value=_empty_agen()),
        patch("tasks.analisis_task.obtener_inexactos_ciiu",
              return_value=_agen([{"idntfccion": "9012345678", "nmbre_rzon_scial": "EMPRESA DOS",
                                   "id_actvdad_ecnmca": "5611"}])),
        patch("tasks.analisis_task.obtener_inexactos_retenciones", return_value=_empty_agen()),
        patch("tasks.analisis_task.with_retry", new=lambda fn, *a, **kw: fn(*a, **kw)),
    ):
        await analizar_proceso(proceso_id, 1, criteria)

    # Verificar transiciones de estado
    estados_llamados = [
        c.args[1] for c in mock_repo.actualizar_estado_proceso.call_args_list
    ]
    assert "PREFILTRANDO" in estados_llamados
    assert "PREFILTRADO_COMPLETADO" in estados_llamados
    assert "EN_PROCESO" in estados_llamados
    assert "COMPLETADO" in estados_llamados

    # Verificar inserción de candidatos
    assert mock_repo.insertar_detalle.call_count == 2
    insert_calls = [c[1] for c in mock_repo.insertar_detalle.call_args_list]
    nits_insertados = [c["nit"] for c in insert_calls]
    assert "9003189639" in nits_insertados
    assert "9012345678" in nits_insertados

    # Verificar clasificaciones correctas
    clasificaciones = {c["nit"]: c["clasificacion"] for c in insert_calls}
    assert clasificaciones["9003189639"] == "OMISO"
    assert clasificaciones["9012345678"] == "INEXACTO"

    # Verificar razón MCP
    tipos_mcp = {c["nit"]: c["mcp_razon"] for c in insert_calls}
    assert tipos_mcp["9003189639"] == "OMISO_CONOCIDO"
    assert tipos_mcp["9012345678"] == "INEXACTO_CIIU"

    # Verificar que se llamó al orquestador para cada candidato
    assert mock_orch.ejecutar.call_count == 2


@pytest.mark.asyncio
async def test_flujo_sin_candidatos_finaliza_completado():
    """Sin candidatos → COMPLETADO inmediato sin orquestador."""
    from tasks.analisis_task import analizar_proceso

    mock_repo = MagicMock()
    mock_repo.actualizar_estado_proceso = AsyncMock()
    mock_repo.actualizar_estado_intento = AsyncMock()
    mock_repo.insertar_detalle = AsyncMock()
    mock_repo.insertar_error_proceso = AsyncMock()

    mock_oc = MagicMock()
    mock_oc.initialize = AsyncMock()

    mock_lookup = MagicMock()
    mock_lookup.get_impuesto_id = AsyncMock(return_value=101)
    mock_lookup.get_programa_id = AsyncMock(return_value=201)
    mock_lookup.get_configuracion_declaracion = AsyncMock(
        return_value=MagicMock(ind_prsntcion_dclrcion="A")
    )
    mock_lookup.get_atributos_ica = AsyncMock(return_value=MagicMock(
        ciiu_ids=[5125], tarifa_ids=[2107],
        ret_recibidas_ids=[2135], ret_practicadas_ids=[2136],
    ))

    with (
        patch("tasks.analisis_task.PostgresProcesoRepo", return_value=mock_repo),
        patch("tasks.analisis_task.OracleClient", return_value=mock_oc),
        patch("tasks.analisis_task.RepositorioLookupOracle", return_value=mock_lookup),
        patch("tasks.analisis_task.obtener_omisos_conocidos", return_value=_empty_agen()),
        patch("tasks.analisis_task.obtener_omisos_desconocidos", return_value=_empty_agen()),
        patch("tasks.analisis_task.obtener_inexactos_ciiu", return_value=_empty_agen()),
        patch("tasks.analisis_task.obtener_inexactos_retenciones", return_value=_empty_agen()),
    ):
        await analizar_proceso(str(uuid.uuid4()), 1, {"periodo": "2024"})

    estado_llamado = any(
        args[0][1] == "COMPLETADO"
        for args in mock_repo.actualizar_estado_proceso.call_args_list
    )
    assert estado_llamado, "Debe haber llamado a actualizar_estado_proceso con COMPLETADO"


@pytest.mark.asyncio
async def test_flujo_con_error_parcial_en_generador():
    """Un generador falla, los otros siguen → procesa los que pueden."""
    from tasks.analisis_task import analizar_proceso

    mock_repo = MagicMock()
    mock_repo.actualizar_estado_proceso = AsyncMock()
    mock_repo.actualizar_estado_intento = AsyncMock()
    mock_repo.insertar_detalle = AsyncMock()
    mock_repo.insertar_error_proceso = AsyncMock()
    mock_repo.insertar_error_detalle = AsyncMock()
    mock_repo.actualizar_progreso_intento = AsyncMock()
    mock_repo.listar_proceso_detalle = AsyncMock(return_value=(1, [
        {"id": 1, "nit": "9003189639", "clasificacion": "INEXACTO"},
    ]))

    mock_orch = MagicMock()
    mock_orch.ejecutar = AsyncMock()

    mock_oc = MagicMock()
    mock_oc.initialize = AsyncMock()

    mock_lookup = MagicMock()
    mock_lookup.get_impuesto_id = AsyncMock(return_value=101)
    mock_lookup.get_programa_id = AsyncMock(side_effect=[201, Exception("Lookup fail")])
    mock_lookup.get_configuracion_declaracion = AsyncMock(
        return_value=MagicMock(ind_prsntcion_dclrcion="A")
    )

    with (
        patch("tasks.analisis_task.PostgresProcesoRepo", return_value=mock_repo),
        patch("tasks.analisis_task.ProcesoOrchestrator", return_value=mock_orch),
        patch("tasks.analisis_task.LLMService", return_value=MagicMock()),
        patch("tasks.analisis_task.OracleClient", return_value=mock_oc),
        patch("tasks.analisis_task.RepositorioLookupOracle", return_value=mock_lookup),
        patch("tasks.analisis_task.obtener_omisos_conocidos",
              return_value=_agen([{"idntfccion": "9003189639", "nmbre_rzon_scial": "OK",
                                   "id_actvdad_ecnmca": "4711"}])),
        patch("tasks.analisis_task.obtener_omisos_desconocidos", return_value=_empty_agen()),
        patch("tasks.analisis_task.obtener_inexactos_ciiu", side_effect=Exception("CIIU error")),
        patch("tasks.analisis_task.obtener_inexactos_retenciones", return_value=_empty_agen()),
        patch("tasks.analisis_task.with_retry", new=lambda fn, *a, **kw: fn(*a, **kw)),
    ):
        await analizar_proceso(str(uuid.uuid4()), 1, {"periodo": "2024"})

    # El generador OMISO_CONOCIDO debe funcionar
    assert mock_repo.insertar_detalle.call_count >= 1
    # El error debe registrarse (INEXACTO_CIIU falló)
    mock_repo.insertar_error_proceso.assert_called()
    # El orquestador debe ejecutar para los candidatos que sí se insertaron
    assert mock_orch.ejecutar.call_count >= 1


# =====================================================================
# Helpers
# =====================================================================


def post_proceso(client_obj, nit_cliente=VALID_CLIENTE_NIT):
    return client_obj.post("/api/v1/proceso", json={
        "cliente_nit": nit_cliente,
        "nombre": "Test proceso",
        "vigencia_ini": "2024-01-01",
        "vigencia_fin": "2024-12-31",
        "tipo_regimen": "COMUN",
        "actividades_economicas": ["4711", "5611"],
        "periodo": "2024",
    })
