import pytest
from fastapi.testclient import TestClient
from api.main import app
from api.deps import get_cache


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def cleanup_overrides():
    yield
    app.dependency_overrides.clear()


def test_health_endpoint_degraded(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert data["version"] == "2.0.0"


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "2.0.0"
    assert data["status"] == "running"


def test_endpoint_404_retorna_error(client):
    response = client.get("/api/v1/nonexistent")
    assert response.status_code == 404


def test_health_with_failing_cache_retorna_500(client):
    async def failing_cache():
        raise RuntimeError("Cache connection failed")

    app.dependency_overrides[get_cache] = failing_cache

    response = client.get("/api/v1/health")
    assert response.status_code == 500
    data = response.json()
    assert "message" in data
