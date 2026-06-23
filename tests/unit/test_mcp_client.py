from infrastructure.mcp.classify import clasificar_nit

from tests.factories import hacer_datos_mcp


def test_clasificacion_desde_mcp_item():
    item = hacer_datos_mcp()
    clasif, detalle = clasificar_nit(item)
    assert clasif in ("OMISO", "EXACTO", "INEXACTO")
    assert isinstance(detalle, str)
    assert len(detalle) > 0


def test_mcp_item_no_candidato_es_exacto():
    item = hacer_datos_mcp(es_candidato=False)
    clasif, _ = clasificar_nit(item)
    assert clasif == "EXACTO"


def test_mcp_item_con_razon_omiso():
    item = hacer_datos_mcp(es_omiso=True, razon="Contribuyente omiso - no presenta declaraciones")
    clasif, _ = clasificar_nit(item)
    assert clasif == "OMISO"


def test_mcp_item_con_score_alto():
    item = hacer_datos_mcp(score_peso=90, es_omiso=False)
    clasif, _ = clasificar_nit(item)
    assert clasif == "INEXACTO"


def test_mcp_item_con_score_bajo():
    item = hacer_datos_mcp(score_peso=10, es_omiso=False)
    clasif, _ = clasificar_nit(item)
    assert clasif == "EXACTO"
