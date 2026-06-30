from infrastructure.mcp.classify import clasificar_candidato, clasificar_nit


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


def test_omiso_por_keyword_en_razon():
    item = {
        "es_candidato": True, "score_peso": 85,
        "razon": "Contribuyente no declaró ICA en el periodo", "es_omiso": False,
    }
    clasif, _ = clasificar_nit(item)
    assert clasif == "OMISO"


def test_inexacto_score_exacto_30():
    item = {"es_candidato": True, "score_peso": 30, "razon": "Diferencia en limite", "es_omiso": False}
    clasif, _ = clasificar_nit(item)
    assert clasif == "INEXACTO"


def test_omiso_por_keyword_sin_declaracion():
    item = {"es_candidato": True, "score_peso": 50, "razon": "sin declaración ICA", "es_omiso": False}
    clasif, _ = clasificar_nit(item)
    assert clasif == "OMISO"


def test_omiso_sin_razon_usa_default():
    item = {"es_candidato": True, "score_peso": 50, "razon": "", "es_omiso": True}
    clasif, detalle = clasificar_nit(item)
    assert clasif == "OMISO"
    assert "No se encontraron declaraciones" in detalle


def test_inexacto_sin_razon_usa_default_con_score():
    item = {"es_candidato": True, "score_peso": 45, "razon": "", "es_omiso": False}
    clasif, detalle = clasificar_nit(item)
    assert clasif == "INEXACTO"
    assert "45" in detalle


def test_clasificar_omiso_conocido():
    item = {"tipo": "OMISO_CONOCIDO", "nit": "9003189639", "razon": "Sin declaracion ICA"}
    clasif, detalle = clasificar_candidato(item)
    assert clasif == "OMISO_CONOCIDO"
    assert "Sin declaracion" in detalle


def test_clasificar_omiso_desconocido():
    item = {"tipo": "OMISO_DESCONOCIDO", "nit": "9012345678", "fuente": "DIAN"}
    clasif, detalle = clasificar_candidato(item)
    assert clasif == "OMISO_DESCONOCIDO"
    assert "DIAN" in detalle


def test_clasificar_inexacto_ciiu():
    item = {
        "tipo": "INEXACTO_CIIU", "nit": "9003189639",
        "ciiu_declarado": "4711", "ciiu_dian": "4721",
        "tarifa_declarada": 0.008, "tarifa_dian": 0.010,
    }
    clasif, detalle = clasificar_candidato(item)
    assert clasif == "INEXACTO_CIIU"
    assert "4711" in detalle
    assert "4721" in detalle


def test_clasificar_inexacto_retenciones():
    item = {
        "tipo": "INEXACTO_RETENCIONES", "nit": "9003189639",
        "diferencia_pct": 25.0,
    }
    clasif, detalle = clasificar_candidato(item)
    assert clasif == "INEXACTO_RETENCIONES"
    assert "25" in detalle


def test_clasificar_candidato_exacto_fallback():
    item = {"nit": "9003189639"}
    clasif, detalle = clasificar_candidato(item)
    assert clasif == "EXACTO"
    assert detalle
