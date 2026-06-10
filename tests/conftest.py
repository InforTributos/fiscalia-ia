import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "microservice"))

import pytest
from api.main import app
from fastapi.testclient import TestClient

from tests.factories import (
    hacer_cruce,
    hacer_inconsistencia,
    hacer_srf,
)


@pytest.fixture(autouse=True)
def cleanup_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def auth_headers():
    return {"X-API-Key": "abc123..."}


@pytest.fixture
def nit_valido():
    return "9003189639"


@pytest.fixture
def periodo_valido():
    return "2025-01"


@pytest.fixture
def datos_cruce_alto():
    return hacer_cruce()


@pytest.fixture
def datos_inconsistencia_alta():
    return hacer_inconsistencia()


@pytest.fixture
def datos_srf_alto():
    return hacer_srf(srf_total=85)


@pytest.fixture
def datos_srf_bajo():
    return hacer_srf(srf_total=15, comp_exogena=5, comp_tarifa=5, comp_omision=3, comp_rues=2)
