def test_health_returns_200(client):
    resp = client.get("/health")
    assert resp.status_code == 200


def test_health_structure(client):
    resp = client.get("/health")
    body = resp.json()
    assert "status" in body
    assert "version" in body
    assert "checks" in body
    assert "uptime_seconds" in body
    assert body["version"] == "2.0.0"
    assert body["status"] in ("healthy", "degraded")
    assert body["checks"]["postgres"] == "ok"


def test_health_always_available(client):
    for _ in range(20):
        resp = client.get("/health")
        assert resp.status_code == 200
