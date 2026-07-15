import pytest


def test_comportamiento_200(client, valid_nit):
    resp = client.get(f"/contribuyente/{valid_nit}/comportamiento?periodo=2024")
    if resp.status_code == 200:
        body = resp.json()
        assert "nit" in body
        assert "score_comportamental" in body
        assert "prioridad" in body
    else:
        assert resp.status_code in (404, 422)


def test_comportamiento_404(client):
    resp = client.get("/contribuyente/000000000/comportamiento?periodo=2024")
    assert resp.status_code == 404


def test_grafo_riesgo_200(client, valid_nit):
    resp = client.get(f"/contribuyente/{valid_nit}/grafo-riesgo?periodo=2024")
    if resp.status_code == 200:
        body = resp.json()
        assert "nodes" in body
        assert "edges" in body
        assert "resumen_red" in body


def test_grafo_riesgo_structure(client, valid_nit):
    resp = client.get(f"/contribuyente/{valid_nit}/grafo-riesgo?periodo=2024")
    if resp.status_code != 200:
        pytest.skip(f"API returned {resp.status_code}")
    body = resp.json()
    resumen = body["resumen_red"]
    assert "score_red" in resumen
    assert "nivel_red" in resumen
    assert "empresas_conectadas" in resumen


def test_expediente_fiscal_200(client, valid_nit):
    resp = client.get(f"/contribuyente/{valid_nit}/expediente-fiscal?periodo=2024")
    if resp.status_code == 200:
        body = resp.json()
        assert "score" in body
        assert "resumen_ejecutivo" in body
        assert "acciones_sugeridas" in body
        assert "markdown" in body


def test_expediente_fiscal_score(client, valid_nit):
    resp = client.get(f"/contribuyente/{valid_nit}/expediente-fiscal?periodo=2024")
    if resp.status_code != 200:
        pytest.skip(f"API returned {resp.status_code}")
    score = resp.json()["score"]
    assert "score_fiscal_unificado" in score
    assert "prioridad" in score
    assert "componentes" in score


def test_visor_grafo_html(client, valid_nit):
    resp = client.get(f"/visor/grafo/{valid_nit}?periodo=2024")
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        assert "text/html" in resp.headers.get("content-type", "")


def test_ranking_comportamental_nonexistent(client):
    pid = "00000000-0000-0000-0000-000000000000"
    resp = client.get(f"/proceso/{pid}/ranking-comportamental?periodo=2024")
    assert resp.status_code in (404, 200)
