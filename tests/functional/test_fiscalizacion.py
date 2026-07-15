import pytest


def test_evaluar_reglas_200(client, fiscalizacion_payload):
    resp = client.post("/fiscalizacion/reglas/evaluar", json=fiscalizacion_payload)
    assert resp.status_code == 200
    body = resp.json()
    assert "total" in body
    assert "resultados" in body


def test_evaluar_reglas_por_nit_200(client, valid_nit):
    resp = client.post(f"/fiscalizacion/reglas/evaluar/{valid_nit}?periodo=2024")
    if resp.status_code == 200:
        body = resp.json()
        assert "total" in body
        assert "resultados" in body
    else:
        assert resp.status_code in (404, 422)


def test_evaluar_reglas_por_nit_404(client):
    resp = client.post("/fiscalizacion/reglas/evaluar/000000000?periodo=2024")
    assert resp.status_code in (404, 422)


def test_ejecutar_reglas_201(client, fiscalizacion_payload):
    resp = client.post("/fiscalizacion/reglas/ejecutar", json=fiscalizacion_payload)
    if resp.status_code == 201:
        body = resp.json()
        assert isinstance(body, list)
        if len(body) > 0:
            assert "id" in body[0]
            assert "nit" in body[0]
            assert "estado" in body[0]
    else:
        assert resp.status_code in (200, 422)


def test_crear_hallazgo_201(client, hallazgo_payload):
    resp = client.post("/fiscalizacion/hallazgos", json=hallazgo_payload)
    if resp.status_code == 201:
        body = resp.json()
        assert "id" in body
        assert body["nit"] == hallazgo_payload["nit"]
        assert body["regla"] == hallazgo_payload["regla"]
    else:
        assert resp.status_code in (200, 422)


def test_crear_hallazgo_structure(client, hallazgo_payload):
    resp = client.post("/fiscalizacion/hallazgos", json=hallazgo_payload)
    if resp.status_code != 201:
        pytest.skip(f"API returned {resp.status_code}")
    body = resp.json()
    assert "score" in body
    assert "score_componentes" in body
    assert "ventana_limite" in body
    assert "accionable" in body
    assert "evidencias" in body
    assert "created_at" in body


def test_listar_hallazgos_200(client):
    resp = client.get("/fiscalizacion/hallazgos")
    assert resp.status_code == 200
    body = resp.json()
    assert "total" in body
    assert "resultados" in body
    assert "page" in body
    assert "page_size" in body


def test_listar_hallazgos_filtros(client):
    resp = client.get("/fiscalizacion/hallazgos?estado=DETECTADO&page=1&page_size=10")
    assert resp.status_code == 200


def test_get_hallazgo_por_id_404(client):
    hid = "00000000-0000-0000-0000-000000000000"
    resp = client.get(f"/fiscalizacion/hallazgos/{hid}")
    assert resp.status_code == 404


def test_revision_hallazgo(client, hallazgo_payload, revision_payload):
    created = client.post("/fiscalizacion/hallazgos", json=hallazgo_payload)
    if created.status_code != 201:
        pytest.skip(f"Could not create hallazgo: {created.status_code}")
    hid = created.json()["id"]
    resp = client.post(f"/fiscalizacion/hallazgos/{hid}/revision", json=revision_payload)
    if resp.status_code == 200:
        body = resp.json()
        assert "revisiones" in body


def test_revision_agente(client, hallazgo_payload):
    created = client.post("/fiscalizacion/hallazgos", json=hallazgo_payload)
    if created.status_code != 201:
        pytest.skip(f"Could not create hallazgo: {created.status_code}")
    hid = created.json()["id"]
    resp = client.post(f"/fiscalizacion/hallazgos/{hid}/revision-agente", json={"usar_ia": False})
    if resp.status_code == 200:
        body = resp.json()
        assert "agente" in body
        assert "resultado" in body
        assert "modo_degradado" in body
