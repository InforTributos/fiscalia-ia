"""Fixtures compartidos para tests E2E.

Mockea a nivel de router (mismo patron que tests/integration/).
TestClient se conecta a la app FastAPI real con mocks de repos.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from main import app

VALID_PROCESO_ID = uuid.uuid4()
VALID_CLIENTE_NIT = "9003189639"


@pytest.fixture(autouse=True)
def bypass_rate_limiter():
    """Desactiva rate limiting para todos los tests E2E."""
    from middleware import rate_limiter as rl
    original = rl.RATE_LIMITS.copy()
    for path in rl.RATE_LIMITS:
        rl.RATE_LIMITS[path] = (999999, 60)
    yield
    rl.RATE_LIMITS.clear()
    rl.RATE_LIMITS.update(original)


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def mock_asyncpg():
    """Mockea asyncpg.create_pool para que la importacion de main no falle."""
    with patch("asyncpg.create_pool") as mock:
        yield mock


@pytest.fixture
def mock_router_repo():
    """Mockea metodos del repo en routers.proceso (mismo patron que integracion)."""
    from routers.proceso import repo as real_repo

    with (
        patch.object(real_repo, "obtener_entidad_por_nit", AsyncMock(return_value={"id": uuid.uuid4(), "nit": VALID_CLIENTE_NIT})),
        patch.object(real_repo, "obtener_proceso_por_criteria", AsyncMock(return_value=None)),
        patch.object(real_repo, "crear_proceso", AsyncMock(return_value=VALID_PROCESO_ID)),
        patch.object(real_repo, "crear_intento", AsyncMock(return_value=1)),
        patch.object(real_repo, "actualizar_estado_proceso", AsyncMock()),
        patch.object(real_repo, "actualizar_estado_intento", AsyncMock()),
        patch.object(real_repo, "insertar_detalle", AsyncMock(return_value=1)),
    ):
        yield
