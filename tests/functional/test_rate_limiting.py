import time


def test_rate_limit_analizar(client, valid_nit):
    statuses = []
    for i in range(7):
        resp = client.post(f"/analizar/{valid_nit}?periodo=2025")
        statuses.append(resp.status_code)
    has_429 = any(s == 429 for s in statuses)
    assert has_429, f"Ninguna solicitud recibio 429: {statuses}"


def test_rate_limit_proceso(client, proceso_payload):
    statuses = []
    for i in range(13):
        resp = client.post("/proceso", json=proceso_payload)
        statuses.append(resp.status_code)
    has_429 = any(s == 429 for s in statuses)
    assert has_429, f"Ninguna solicitud recibio 429: {statuses}"


def test_rate_limit_health_unlimited(client):
    for _ in range(30):
        resp = client.get("/health")
        assert resp.status_code == 200


def test_rate_limit_resets_after_window(client, valid_nit):
    for _ in range(6):
        client.post(f"/analizar/{valid_nit}?periodo=2025")
    time.sleep(62)
    resp = client.post(f"/analizar/{valid_nit}?periodo=2025")
    assert resp.status_code in (200, 404, 500)
