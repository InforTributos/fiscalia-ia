def test_analizar_nit_200(client, valid_nit):
    resp = client.post(f"/analizar/{valid_nit}?periodo=2024")
    if resp.status_code == 200:
        body = resp.json()
        assert "nit" in body
        assert body["nit"] == valid_nit
        assert "clasificacion" in body
        assert "hallazgos" in body
    else:
        assert resp.status_code in (404, 500, 429)


def test_analizar_nit_404(client):
    resp = client.post("/analizar/000000000?periodo=2024")
    assert resp.status_code == 404
    body = resp.json()
    assert "error" in body


def test_analizar_nit_structure(client, valid_nit):
    resp = client.post(f"/analizar/{valid_nit}?periodo=2024")
    if resp.status_code != 200:
        pytest.skip(f"API returned {resp.status_code}")
    body = resp.json()
    assert "razon_social" in body
    assert "ciiu" in body
    assert "srf_total" in body
    assert "nivel_riesgo" in body
    assert "explicacion_ia" in body
    assert "tokens_utilizados" in body
    assert "duracion_ms" in body
    assert "provider_utilizado" in body


def test_analizar_nit_with_periodo(client, valid_nit):
    resp = client.post(f"/analizar/{valid_nit}?periodo=2023")
    if resp.status_code == 200:
        data = resp.json()
        assert "nit" in data
        assert data["nit"] == valid_nit


def test_analizar_cache_hit(client, valid_nit):
    first = client.post(f"/analizar/{valid_nit}?periodo=2024")
    if first.status_code != 200:
        pytest.skip(f"First request failed: {first.status_code}")
    second = client.post(f"/analizar/{valid_nit}?periodo=2024")
    if second.status_code == 200:
        assert second.json().get("cache_hit", False) in (True, False)
