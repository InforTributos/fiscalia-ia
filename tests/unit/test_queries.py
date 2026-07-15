import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from infrastructure.persistence import queries

UUID1 = uuid.uuid4()
UUID2 = uuid.uuid4()


@pytest.fixture
def mock_conn():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock()
    conn.fetch = AsyncMock()
    conn.fetchval = AsyncMock()
    conn.execute = AsyncMock()
    return conn


@pytest.fixture
def mock_pool(mock_conn):
    pool = MagicMock()
    pool.acquire.return_value.__aenter__.return_value = mock_conn
    return pool, mock_conn


# ── crear_cliente ──

@patch("infrastructure.persistence.queries.get_pool")
async def test_crear_cliente(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchrow.return_value = {"id": UUID1}

    result = await queries.crear_cliente("9003189639", "EMPRESA S.A.", "email@test.com")
    assert result == UUID1
    conn.fetchrow.assert_awaited_once()


@patch("infrastructure.persistence.queries.get_pool")
async def test_crear_cliente_sin_email(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchrow.return_value = {"id": UUID1}

    result = await queries.crear_cliente("9003189639", "EMPRESA S.A.")
    assert result == UUID1


@patch("infrastructure.persistence.queries.get_pool")
async def test_crear_cliente_retorna_none(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchrow.return_value = None

    result = await queries.crear_cliente("9003189639", "EMPRESA S.A.")
    assert result is None


# ── obtener_cliente_por_nit ──

@patch("infrastructure.persistence.queries.get_pool")
async def test_obtener_cliente_por_nit(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchrow.return_value = {"id": UUID1, "nit": "9003189639"}

    result = await queries.obtener_cliente_por_nit("9003189639")
    assert result["nit"] == "9003189639"


@patch("infrastructure.persistence.queries.get_pool")
async def test_obtener_cliente_por_nit_no_encontrado(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchrow.return_value = None

    result = await queries.obtener_cliente_por_nit("9999999999")
    assert result is None


# ── crear_proceso ──

@patch("infrastructure.persistence.queries.get_pool")
async def test_crear_proceso(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchrow.return_value = {"id": UUID1}

    result = await queries.crear_proceso(UUID2, "Test", {"periodo": "2024"})
    assert result == UUID1


@patch("infrastructure.persistence.queries.get_pool")
async def test_crear_proceso_retorna_none(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchrow.return_value = None

    result = await queries.crear_proceso(UUID2, "Test", {"periodo": "2024"})
    assert result is None


# ── obtener_proceso_por_criteria ──

@patch("infrastructure.persistence.queries.get_pool")
async def test_obtener_proceso_por_criteria(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchrow.return_value = {"id": UUID1, "criteria": {"periodo": "2024"}}

    result = await queries.obtener_proceso_por_criteria(UUID2, {"periodo": "2024"})
    assert result["id"] == UUID1


@patch("infrastructure.persistence.queries.get_pool")
async def test_obtener_proceso_por_criteria_no_encontrado(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchrow.return_value = None

    result = await queries.obtener_proceso_por_criteria(UUID2, {"periodo": "2024"})
    assert result is None


# ── obtener_proceso ──

@patch("infrastructure.persistence.queries.get_pool")
async def test_obtener_proceso(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchrow.return_value = {"id": UUID1, "estado": "PENDIENTE"}

    result = await queries.obtener_proceso(UUID1)
    assert result["id"] == UUID1


@patch("infrastructure.persistence.queries.get_pool")
async def test_obtener_proceso_no_encontrado(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchrow.return_value = None

    result = await queries.obtener_proceso(UUID1)
    assert result is None


# ── crear_intento ──

@patch("infrastructure.persistence.queries.get_pool")
async def test_crear_intento(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchrow.return_value = {"id": 1}

    result = await queries.crear_intento(UUID1)
    assert result == 1


@patch("infrastructure.persistence.queries.get_pool")
async def test_crear_intento_con_numero(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchrow.return_value = {"id": 2}

    result = await queries.crear_intento(UUID1, numero=2)
    assert result == 2


@patch("infrastructure.persistence.queries.get_pool")
async def test_crear_intento_retorna_none(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchrow.return_value = None

    result = await queries.crear_intento(UUID1)
    assert result is None


# ── obtener_intento ──

@patch("infrastructure.persistence.queries.get_pool")
async def test_obtener_intento(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchrow.return_value = {"id": 1, "estado": "EN_PROCESO"}

    result = await queries.obtener_intento(1)
    assert result["id"] == 1


# ── obtener_ultimo_intento ──

@patch("infrastructure.persistence.queries.get_pool")
async def test_obtener_ultimo_intento(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchrow.return_value = {"id": 2, "numero_intento": 2}

    result = await queries.obtener_ultimo_intento(UUID1)
    assert result["numero_intento"] == 2


# ── actualizar_estado_intento ──

@patch("infrastructure.persistence.queries.get_pool")
async def test_actualizar_estado_intento_completado(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool

    await queries.actualizar_estado_intento(1, "COMPLETADO")
    conn.execute.assert_awaited_once()


@patch("infrastructure.persistence.queries.get_pool")
async def test_actualizar_estado_intento_error(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool

    await queries.actualizar_estado_intento(1, "ERROR")
    conn.execute.assert_awaited_once()


@patch("infrastructure.persistence.queries.get_pool")
async def test_actualizar_estado_intento_error_con_resumen(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool

    await queries.actualizar_estado_intento(1, "ERROR", "Fallo critico")
    conn.execute.assert_awaited_once()


@patch("infrastructure.persistence.queries.get_pool")
async def test_actualizar_estado_intento_intermedio(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool

    await queries.actualizar_estado_intento(1, "EN_PROCESO")
    conn.execute.assert_awaited_once()


# ── actualizar_progreso_intento ──

@patch("infrastructure.persistence.queries.get_pool")
async def test_actualizar_progreso_intento(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool

    await queries.actualizar_progreso_intento(1, 5, 1)
    conn.execute.assert_awaited_once()


# ── insertar_detalle ──

@patch("infrastructure.persistence.queries.get_pool")
async def test_insertar_detalle(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchrow.return_value = {"id": 42}

    result = await queries.insertar_detalle(UUID1, 1, "9003189639", "OMISO")
    assert result == 42


@patch("infrastructure.persistence.queries.get_pool")
async def test_insertar_detalle_completo(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchrow.return_value = {"id": 43}

    result = await queries.insertar_detalle(
        UUID1, 1, "9003189639", "INEXACTO",
        razon_social="EMPRESA S.A.", ciiu="4711",
        mcp_score=85.0, es_candidato=True, mcp_razon="CIIU mismatch",
    )
    assert result == 43


# ── actualizar_resultado_detalle ──

@patch("infrastructure.persistence.queries.get_pool")
async def test_actualizar_resultado_detalle(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool

    await queries.actualizar_resultado_detalle(1, 75.0, "ALTO", [], "Explicacion", 100, 50, 0.01)
    conn.execute.assert_awaited_once()


# ── actualizar_score_detalle ──

@patch("infrastructure.persistence.queries.get_pool")
async def test_actualizar_score_detalle(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool

    await queries.actualizar_score_detalle(1, 85.5)
    conn.execute.assert_awaited_once()


# ── mergear_criteria_proceso ──

@patch("infrastructure.persistence.queries.get_pool")
async def test_mergear_criteria_proceso(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool

    await queries.mergear_criteria_proceso(UUID1, {"resumen_campana": "test"})
    conn.execute.assert_awaited_once()


# ── mergear_hallazgos_detalle ──

@patch("infrastructure.persistence.queries.get_pool")
async def test_mergear_hallazgos_detalle(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool

    hallazgos = [{"tipo": "OMISO", "severidad": "ALTA"}]
    await queries.mergear_hallazgos_detalle(1, hallazgos)
    conn.execute.assert_awaited_once()


# ── insertar_error_proceso ──

@patch("infrastructure.persistence.queries.get_pool")
async def test_insertar_error_proceso(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool

    await queries.insertar_error_proceso(UUID1, 1, "MCP", "MCP_TIMEOUT", "timeout")
    conn.execute.assert_awaited_once()


@patch("infrastructure.persistence.queries.get_pool")
async def test_insertar_error_proceso_con_contexto(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool

    await queries.insertar_error_proceso(UUID1, 1, "MCP", "MCP_TIMEOUT", "timeout", {"nit": "9003189639"})
    conn.execute.assert_awaited_once()


# ── insertar_error_detalle ──

@patch("infrastructure.persistence.queries.get_pool")
async def test_insertar_error_detalle(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool

    await queries.insertar_error_detalle(UUID1, 1, "9003189639", "LLM", "LLM_TIMEOUT", "timeout")
    conn.execute.assert_awaited_once()


@patch("infrastructure.persistence.queries.get_pool")
async def test_insertar_error_detalle_con_contexto(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool

    await queries.insertar_error_detalle(UUID1, 1, "9003189639", "LLM", "LLM_TIMEOUT", "timeout", {"tokens": 100})
    conn.execute.assert_awaited_once()


# ── listar_proceso_detalle ──

@patch("infrastructure.persistence.queries.get_pool")
async def test_listar_proceso_detalle_sin_filtros(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchval.return_value = 2
    conn.fetch.return_value = [
        {"id": 1, "nit": "9003189639"},
        {"id": 2, "nit": "9003189640"},
    ]

    total, rows = await queries.listar_proceso_detalle(UUID1)
    assert total == 2
    assert len(rows) == 2


@patch("infrastructure.persistence.queries.get_pool")
async def test_listar_proceso_detalle_con_filtros(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchval.return_value = 1
    conn.fetch.return_value = [{"id": 1, "nit": "9003189639", "mcp_score": 85.0}]

    total, rows = await queries.listar_proceso_detalle(
        UUID1, intento_id=1, clasificacion="OMISO", min_score=50.0,
    )
    assert total == 1


@patch("infrastructure.persistence.queries.get_pool")
async def test_listar_proceso_detalle_con_paginacion(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchval.return_value = 3
    conn.fetch.return_value = [{"id": 1, "nit": "9003189639"}]

    total, rows = await queries.listar_proceso_detalle(UUID1, page=2, page_size=10)
    assert total == 3


# ── listar_errores ──

@patch("infrastructure.persistence.queries.get_pool")
async def test_listar_errores(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetch.return_value = [{"id": 1, "capa": "MCP"}]

    err_proc, err_det = await queries.listar_errores(UUID1)
    assert len(err_proc) == 1


@patch("infrastructure.persistence.queries.get_pool")
async def test_listar_errores_con_filtros(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetch.return_value = [{"id": 1, "capa": "MCP"}]

    err_proc, err_det = await queries.listar_errores(UUID1, intento_id=1, capa="MCP", nit="9003189639")
    assert len(err_proc) == 1


# ── actualizar_estado_proceso ──

@patch("infrastructure.persistence.queries.get_pool")
async def test_actualizar_estado_proceso(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool

    await queries.actualizar_estado_proceso(UUID1, "COMPLETADO", total_nits=10, candidatos=5)
    conn.execute.assert_awaited_once()


@patch("infrastructure.persistence.queries.get_pool")
async def test_actualizar_estado_proceso_simple(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool

    await queries.actualizar_estado_proceso(UUID1, "ERROR")
    conn.execute.assert_awaited_once()


# ── obtener_historial_intentos ──

@patch("infrastructure.persistence.queries.get_pool")
async def test_obtener_historial_intentos(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetch.return_value = [{"id": 1, "numero_intento": 1}, {"id": 2, "numero_intento": 2}]

    result = await queries.obtener_historial_intentos(UUID1)
    assert len(result) == 2


@patch("infrastructure.persistence.queries.get_pool")
async def test_obtener_historial_intentos_vacio(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetch.return_value = []

    result = await queries.obtener_historial_intentos(UUID1)
    assert result == []


# ── obtener_cliente_por_id ──

@patch("infrastructure.persistence.queries.get_pool")
async def test_obtener_cliente_por_id(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchrow.return_value = {"id": UUID1, "nit": "9003189639"}

    result = await queries.obtener_cliente_por_id(UUID1)
    assert result["id"] == UUID1


@patch("infrastructure.persistence.queries.get_pool")
async def test_obtener_cliente_por_id_no_encontrado(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchrow.return_value = None

    result = await queries.obtener_cliente_por_id(UUID1)
    assert result is None
