def test_create_proceso_completo_201(client, proceso_payload):
    """POST /proceso con tipo=COMPLETO funciona igual que campana antes"""
    payload = {**proceso_payload, "tipo": "COMPLETO"}
    resp = client.post("/proceso", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert "proceso_id" in body
    assert body["estado"] in ("EN_COLA", "PREFILTRANDO")


def test_create_proceso_completo_respuesta(client, proceso_payload):
    """POST /proceso tipo=COMPLETO devuelve estructura completa"""
    payload = {**proceso_payload, "tipo": "COMPLETO"}
    resp = client.post("/proceso", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert "nombre" in body
    assert "entidad_nit" in body
    assert "resumen" in body
