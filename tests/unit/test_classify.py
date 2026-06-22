from infrastructure.mcp.classify import clasificar_nit


def test_clasificacion_omiso():
    item = {"es_candidato": True, "score_peso": 85, "es_omiso": True, "razon": "No declaró ICA"}
    clasif, detalle = clasificar_nit(item)
    assert clasif == "OMISO"
    assert detalle


def test_clasificacion_exacto():
    item = {"es_candidato": False, "score_peso": 0, "razon": ""}
    clasif, detalle = clasificar_nit(item)
    assert clasif == "EXACTO"
    assert detalle


def test_clasificacion_inexacto():
    item = {"es_candidato": True, "score_peso": 45, "razon": "Diferencia del 45%"}
    clasif, detalle = clasificar_nit(item)
    assert clasif == "INEXACTO"
    assert detalle


def test_clasificacion_exacto_score_bajo():
    item = {"es_candidato": True, "score_peso": 15, "razon": "Diferencia menor", "es_omiso": False}
    clasif, _ = clasificar_nit(item)
    assert clasif == "EXACTO"
