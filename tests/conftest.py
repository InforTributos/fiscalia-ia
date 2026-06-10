import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "microservice"))

import pytest
from fastapi.testclient import TestClient
from api.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"X-API-Key": "abc123..."}
