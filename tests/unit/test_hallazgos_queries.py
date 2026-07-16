import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from infrastructure.persistence import hallazgos_queries

UUID1 = uuid.uuid4()


@pytest.fixture
def mock_conn():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock()
    conn.fetch = AsyncMock()
    conn.fetchval = AsyncMock()
    conn.execute = AsyncMock()
    conn.transaction = MagicMock()
    conn.transaction.return_value.__aenter__ = AsyncMock(return_value=conn)
    conn.transaction.return_value.__aexit__ = AsyncMock(return_value=None)
    return conn


@pytest.fixture
def mock_pool(mock_conn):
    pool = MagicMock()
    pool.acquire.return_value.__aenter__.return_value = mock_conn
    return pool, mock_conn


@pytest.fixture
def minimal_hallazgo_data():
    return {
        "contribuyente_nit": "9003189639",
        "regla": "SRF-001",
        "periodo": "2024",
        "tipo_hallazgo": "OMISO",
        "fuerza_probatoria": 0.85,
        "score": 90.0,
        "ventana_limite": "2025-06-30",
        "accionable": True,
    }


# ── crear_hallazgo ──

@patch("infrastructure.persistence.hallazgos_queries.get_pool")
async def test_crear_hallazgo(mock_get_pool, mock_pool, minimal_hallazgo_data):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchrow.return_value = {"id": 1, **minimal_hallazgo_data}

    result = await hallazgos_queries.crear_hallazgo(minimal_hallazgo_data, [])
    assert result["id"] == 1


@patch("infrastructure.persistence.hallazgos_queries.get_pool")
async def test_crear_hallazgo_con_evidencias(mock_get_pool, mock_pool, minimal_hallazgo_data):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchrow.return_value = {"id": 2, **minimal_hallazgo_data}

    evidencias = [
        {"fuente": "DIAN", "descripcion": "Registro en RUES", "referencia_registro": "RUES-123"},
    ]
    result = await hallazgos_queries.crear_hallazgo(minimal_hallazgo_data, evidencias)
    assert result["id"] == 2


@patch("infrastructure.persistence.hallazgos_queries.get_pool")
async def test_crear_hallazgo_con_todos_los_campos(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchrow.return_value = {"id": 3, "contribuyente_nit": "9003189639"}

    data = {
        "contribuyente_nit": "9003189639",
        "regla": "SRF-002",
        "periodo": "2024",
        "tipo_hallazgo": "INEXACTO",
        "fuerza_probatoria": 0.75,
        "brecha_valor": 5000000.0,
        "impuesto_estimado": 15000000.0,
        "score": 80.0,
        "score_componentes": {"base": 0.8, "gravable": 0.7},
        "ventana_limite": "2025-06-30",
        "accionable": True,
        "estado": "DETECTADO",
        "resumen": "Discrepancia en ingresos reportados",
        "metadata": {"fuente": "DIAN", "confianza": 0.95},
    }
    result = await hallazgos_queries.crear_hallazgo(data, [])
    assert result["id"] == 3


# ── obtener_hallazgo ──

@patch("infrastructure.persistence.hallazgos_queries.get_pool")
async def test_obtener_hallazgo(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchrow.return_value = {"id": UUID1, "tipo_hallazgo": "OMISO"}
    conn.fetch.return_value = []

    result = await hallazgos_queries.obtener_hallazgo(UUID1)
    assert result["id"] == UUID1


@patch("infrastructure.persistence.hallazgos_queries.get_pool")
async def test_obtener_hallazgo_no_encontrado(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchrow.return_value = None

    result = await hallazgos_queries.obtener_hallazgo(UUID1)
    assert result is None


@patch("infrastructure.persistence.hallazgos_queries.get_pool")
async def test_obtener_hallazgo_con_evidencias_y_revisiones(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchrow.return_value = {"id": UUID1, "tipo_hallazgo": "OMISO"}
    conn.fetch.side_effect = [
        [{"id": 10, "fuente": "DIAN", "snapshot": "{}"}],
        [{"id": 20, "funcionario_id": "FUNC-001", "decision": "VALIDAR"}],
        [{"id": 30, "agente": "AGT-01", "version": "1.0", "resultado": "{}"}],
    ]

    result = await hallazgos_queries.obtener_hallazgo(UUID1)
    assert result["id"] == UUID1
    assert len(result["evidencias"]) == 1
    assert len(result["revisiones"]) == 1
    assert len(result["revisiones_agente"]) == 1


# ── listar_hallazgos ──

@patch("infrastructure.persistence.hallazgos_queries.get_pool")
async def test_listar_hallazgos(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchval.return_value = 2
    conn.fetch.return_value = [
        {"id": 1, "tipo_hallazgo": "OMISO"},
        {"id": 2, "tipo_hallazgo": "INEXACTO"},
    ]

    total, rows = await hallazgos_queries.listar_hallazgos()
    assert total == 2
    assert len(rows) == 2


@patch("infrastructure.persistence.hallazgos_queries.get_pool")
async def test_listar_hallazgos_vacio(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchval.return_value = 0
    conn.fetch.return_value = []

    total, rows = await hallazgos_queries.listar_hallazgos()
    assert total == 0
    assert rows == []


@patch("infrastructure.persistence.hallazgos_queries.get_pool")
async def test_listar_hallazgos_filtro_estado(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchval.return_value = 1
    conn.fetch.return_value = [{"id": 1, "tipo_hallazgo": "OMISO", "estado": "DETECTADO"}]

    total, rows = await hallazgos_queries.listar_hallazgos(estado="DETECTADO")
    assert total == 1


@patch("infrastructure.persistence.hallazgos_queries.get_pool")
async def test_listar_hallazgos_filtro_nit(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchval.return_value = 1
    conn.fetch.return_value = [{"id": 1, "contribuyente_nit": "9003189639"}]

    total, rows = await hallazgos_queries.listar_hallazgos(contribuyente_nit="9003189639")
    assert total == 1


@patch("infrastructure.persistence.hallazgos_queries.get_pool")
async def test_listar_hallazgos_filtro_accionable(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchval.return_value = 1
    conn.fetch.return_value = [{"id": 1, "accionable": True}]

    total, rows = await hallazgos_queries.listar_hallazgos(accionable=True)
    assert total == 1


@patch("infrastructure.persistence.hallazgos_queries.get_pool")
async def test_listar_hallazgos_filtro_regla(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchval.return_value = 1
    conn.fetch.return_value = [{"id": 1, "regla": "SRF-001"}]

    total, rows = await hallazgos_queries.listar_hallazgos(regla="SRF-001")
    assert total == 1


@patch("infrastructure.persistence.hallazgos_queries.get_pool")
async def test_listar_hallazgos_con_paginacion(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchval.return_value = 10
    conn.fetch.return_value = [{"id": 1}]

    total, rows = await hallazgos_queries.listar_hallazgos(page=2, page_size=5)
    assert total == 10


# ── registrar_revision ──

@patch("infrastructure.persistence.hallazgos_queries.get_pool")
async def test_registrar_revision(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchrow.side_effect = [
        {"id": UUID1, "tipo_hallazgo": "OMISO"},
        {"id": UUID1, "tipo_hallazgo": "OMISO"},
    ]
    conn.fetch.return_value = []

    result = await hallazgos_queries.registrar_revision(UUID1, "FUNC-001", "VALIDAR", "motivo")
    assert result is not None


@patch("infrastructure.persistence.hallazgos_queries.get_pool")
async def test_registrar_revision_no_encontrado(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchrow.return_value = None

    result = await hallazgos_queries.registrar_revision(UUID1, "FUNC-001", "VALIDAR", "motivo")
    assert result is None


@patch("infrastructure.persistence.hallazgos_queries.get_pool")
async def test_registrar_revision_descartar(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchrow.side_effect = [
        {"id": UUID1, "tipo_hallazgo": "OMISO"},
        {"id": UUID1, "tipo_hallazgo": "OMISO"},
    ]
    conn.fetch.return_value = []

    result = await hallazgos_queries.registrar_revision(UUID1, "FUNC-002", "DESCARTAR", "sin fundamento")
    assert result is not None


@patch("infrastructure.persistence.hallazgos_queries.get_pool")
async def test_registrar_revision_pedir_info(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchrow.side_effect = [
        {"id": UUID1, "tipo_hallazgo": "OMISO"},
        {"id": UUID1, "tipo_hallazgo": "OMISO"},
    ]
    conn.fetch.return_value = []

    result = await hallazgos_queries.registrar_revision(
        UUID1, "FUNC-003", "PEDIR_INFO", motivo="solicitar documentos",
    )
    assert result is not None


# ── registrar_revision_agente ──

@patch("infrastructure.persistence.hallazgos_queries.get_pool")
async def test_registrar_revision_agente(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchrow.return_value = {"id": 100, "hallazgo_id": UUID1}

    result = await hallazgos_queries.registrar_revision_agente(
        UUID1, "AGT-01", "1.0", {"srf_score": 85.0}, False,
    )
    assert result["id"] == 100


@patch("infrastructure.persistence.hallazgos_queries.get_pool")
async def test_registrar_revision_agente_con_tokens(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchrow.return_value = {"id": 101, "hallazgo_id": UUID1}

    result = await hallazgos_queries.registrar_revision_agente(
        UUID1, "AGT-02", "2.0", {},
        True, tokens_entrada=500, tokens_salida=200,
    )
    assert result["id"] == 101


@patch("infrastructure.persistence.hallazgos_queries.get_pool")
async def test_registrar_revision_agente_degradado(mock_get_pool, mock_pool):
    pool, conn = mock_pool
    mock_get_pool.return_value = pool
    conn.fetchrow.return_value = {"id": 102, "hallazgo_id": UUID1}

    result = await hallazgos_queries.registrar_revision_agente(
        UUID1, "AGT-03", "1.5", {"error": "LLM timeout"}, True,
    )
    assert result["id"] == 102
