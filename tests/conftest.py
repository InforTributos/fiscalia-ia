import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "microservice"))

import pytest
from main import app
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def cleanup_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def nit_valido():
    return "9003189639"


@pytest.fixture
def periodo_valido():
    return "2024"
