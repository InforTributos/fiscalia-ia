def test_create_campana_201(client, campana_payload):
    resp = client.post("/campana", json=campana_payload)
    assert resp.status_code == 201
    body = resp.json()
    assert "proceso_id" in body
    assert body["estado"] in ("EN_COLA", "PREFILTRANDO")


def test_create_campana_defaults(client):
    resp = client.post("/campana", json={"periodo": "2024"})
    assert resp.status_code == 201
    body = resp.json()
    assert "nombre" in body
    assert "mensaje" in body


def test_create_campana_with_ciiu(client):
    resp = client.post("/campana", json={
        "periodo": "2024",
        "actividad_economica": "4711",
        "nombre": "Campana Comercio 2024",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["estado"] in ("EN_COLA", "PREFILTRANDO")
