from domain.services.crosscheck_service import (
    calcular_srf, clasificar_por_datos, extraer_inconsistencias,
    PESO_EXOGENA, PESO_OMISION, PESO_TARIFA, PESO_RUES,
)


def test_clasifica_omiso():
    datos = {"nit": "9003189639", "declaraciones_ica": [], "exogena_dian": [], "rues_estado": "ACTIVO"}
    assert clasificar_por_datos(datos) == "OMISO"


def test_clasifica_inexacto():
    datos = {
        "nit": "9003189639",
        "declaraciones_ica": [{"periodo": "2024-B1", "base_gravable": 50000000, "tarifa": 0.01, "impuesto": 500000}],
        "exogena_dian": [{"periodo": "2024", "ingresos": 120000000}],
        "rues_estado": "ACTIVO",
    }
    assert clasificar_por_datos(datos) == "INEXACTO"


def test_extrae_inconsistencias():
    datos = {
        "nit": "9003189639",
        "ciiu": "4711",
        "declaraciones_ica": [{"periodo": "2024-B1", "base_gravable": 50000000, "tarifa": 0.008, "impuesto": 400000}],
        "exogena_dian": [{"periodo": "2024", "ingresos": 120000000}],
    }
    incs = extraer_inconsistencias(datos)
    assert len(incs) > 0
    assert incs[0]["tipo"] == "SUBDECLARACION_EXOGENA"


def test_srf_4_componentes():
    datos = {
        "ciiu": "4711",
        "declaraciones_ica": [
            {"periodo": "2024-B1", "base_gravable": 50000000, "tarifa": 0.008, "impuesto": 400000},
            {"periodo": "2024-B2", "base_gravable": 60000000, "tarifa": 0.008, "impuesto": 480000},
        ],
        "exogena_dian": [{"periodo": "2024", "ingresos": 120000000}],
        "rues_estado": "ACTIVO",
    }
    result = calcular_srf(datos)
    assert "srf_total" in result
    assert "componentes" in result
    comps = result["componentes"]
    assert "diferencia_exogena" in comps
    assert "antiguedad_omision" in comps
    assert "discrepancia_tarifa" in comps
    assert "estado_rues" in comps
    assert 0 <= result["srf_total"] <= 100


def test_srf_omiso_sin_declaraciones():
    datos = {
        "ciiu": "4711",
        "declaraciones_ica": [],
        "exogena_dian": [],
        "rues_estado": "",
    }
    result = calcular_srf(datos)
    comps = result["componentes"]
    assert comps["antiguedad_omision"]["valor"] == PESO_OMISION
    assert comps["estado_rues"]["valor"] == PESO_RUES * 0.5


def test_srf_rues_inactivo():
    datos = {
        "ciiu": "4711",
        "declaraciones_ica": [{"periodo": "2024-B1", "base_gravable": 1000000, "tarifa": 0.008, "impuesto": 8000}],
        "exogena_dian": [{"periodo": "2024", "ingresos": 1000000}],
        "rues_estado": "INACTIVO",
    }
    result = calcular_srf(datos)
    assert result["componentes"]["estado_rues"]["valor"] == PESO_RUES


def test_srf_exogena_match():
    datos = {
        "ciiu": "4711",
        "declaraciones_ica": [{"periodo": "2024-B1", "base_gravable": 1000000, "tarifa": 0.008, "impuesto": 8000}],
        "exogena_dian": [{"periodo": "2024", "ingresos": 1000000}],
        "rues_estado": "ACTIVO",
    }
    result = calcular_srf(datos)
    assert result["componentes"]["diferencia_exogena"]["valor"] == 0


def test_clasifica_exacto_sin_datos():
    datos = {"nit": "9003189639", "declaraciones_ica": [{"base_gravable": 1000}], "exogena_dian": []}
    assert clasificar_por_datos(datos) == "INEXACTO"
