from api.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health_endpoint_retorna_200():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data


def test_root_endpoint_retorna_info():
    response = client.get("/")
    assert response.status_code == 200
    assert "version" in response.json()
