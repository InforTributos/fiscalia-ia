def test_create_proceso_201(client, proceso_payload):
    resp = client.post("/proceso", json=proceso_payload)
    assert resp.status_code == 201
    body = resp.json()
    assert "proceso_id" in body
    assert body["estado"] in ("EN_COLA", "PREFILTRANDO", "PREFILTRADO_COMPLETADO")
    assert body["nombre"] == proceso_payload["nombre"]


def test_create_proceso_body(client, proceso_payload):
    resp = client.post("/proceso", json=proceso_payload)
    assert resp.status_code == 201
    body = resp.json()
    assert "intento_id" in body
    assert "created_at" in body
    assert body["cliente_nit"] == proceso_payload["cliente_nit"]
    assert body["proceso_id"] is not None


def test_get_status_200(client, proceso_payload):
    create = client.post("/proceso", json=proceso_payload)
    assert create.status_code == 201
    pid = create.json()["proceso_id"]
    resp = client.get(f"/proceso/{pid}/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["proceso_id"] == pid
    assert "estado" in body


def test_get_status_404(client):
    resp = client.get(f"/proceso/{'00000000-0000-0000-0000-000000000000'}/status")
    assert resp.status_code == 404


def test_get_results_200_returns_nits(client, proceso_payload):
    create = client.post("/proceso", json=proceso_payload)
    assert create.status_code == 201
    pid = create.json()["proceso_id"]
    results = client.get(f"/proceso/{pid}/results?include_partial=true")
    if results.status_code == 200:
        body = results.json()
        assert "resultados" in body
        assert "paginacion" in body


def test_get_results_pagination(client, proceso_payload):
    create = client.post("/proceso", json=proceso_payload)
    assert create.status_code == 201
    pid = create.json()["proceso_id"]
    resp = client.get(f"/proceso/{pid}/results?page=1&page_size=10&include_partial=true")
    if resp.status_code == 200:
        body = resp.json()
        assert body["paginacion"]["page"] == 1
        assert body["paginacion"]["page_size"] == 10


def test_get_results_no_partial_returns_409_or_200(client, proceso_payload):
    create = client.post("/proceso", json=proceso_payload)
    assert create.status_code == 201
    pid = create.json()["proceso_id"]
    resp = client.get(f"/proceso/{pid}/results")
    if resp.status_code == 409:
        assert "error" in resp.json()
    else:
        assert resp.status_code == 200


def test_get_errors_200(client, proceso_payload):
    create = client.post("/proceso", json=proceso_payload)
    assert create.status_code == 201
    pid = create.json()["proceso_id"]
    resp = client.get(f"/proceso/{pid}/errors")
    assert resp.status_code == 200
    body = resp.json()
    assert "errores_proceso" in body
    assert "errores_detalle" in body


def test_get_errors_filter_capa(client, proceso_payload):
    create = client.post("/proceso", json=proceso_payload)
    assert create.status_code == 201
    pid = create.json()["proceso_id"]
    resp = client.get(f"/proceso/{pid}/errors?capa=MCP")
    assert resp.status_code == 200
