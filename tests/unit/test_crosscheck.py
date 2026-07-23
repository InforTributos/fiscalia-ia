from domain.services.crosscheck_service import (
    PESO_OMISION,
    PESO_RUES,
    calcular_srf,
    clasificar_por_datos,
    extraer_inconsistencias,
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


def test_clasificar_omiso_conocido_en_datos():
    datos = {
        "nit": "9003189639", "tipo": "OMISO_CONOCIDO",
        "declaraciones_ica": [], "exogena_dian": [],
    }
    assert clasificar_por_datos(datos) == "OMISO_CONOCIDO"


def test_clasificar_omiso_desconocido_en_datos():
    datos = {
        "nit": "9012345678", "tipo": "OMISO_DESCONOCIDO",
        "fuente": "DIAN", "declaraciones_ica": [],
    }
    assert clasificar_por_datos(datos) == "OMISO_DESCONOCIDO"


def test_inexacto_ciiu_genera_inconsistencia():
    datos = {
        "nit": "9003189639", "tipo": "INEXACTO_CIIU",
        "ciiu": "4711", "ciiu_dian": "4721",
        "ciiu_declarado": "4711",
        "tarifa_declarada": 0.008, "tarifa_dian": 0.010,
        "declaraciones_ica": [{"periodo": "2024-B1", "base_gravable": 50000000, "tarifa": 0.008, "impuesto": 400000}],
        "exogena_dian": [],
    }
    incs = extraer_inconsistencias(datos)
    ciiu_incs = [i for i in incs if i["tipo"] == "TARIFA_INCORRECTA_CIIU"]
    assert len(ciiu_incs) == 1
    assert ciiu_incs[0]["ciiu_declarado"] == "4711"
    assert ciiu_incs[0]["ciiu_dian"] == "4721"


def test_inexacto_retenciones_genera_inconsistencia():
    datos = {
        "nit": "9003189639", "tipo": "INEXACTO_RETENCIONES",
        "diferencia_pct": 25.0,
        "retenciones_declaradas_practicadas": 500000,
        "retenciones_exogena_practicadas": 750000,
        "declaraciones_ica": [{"periodo": "2024-B1", "base_gravable": 50000000, "tarifa": 0.008, "impuesto": 400000}],
        "exogena_dian": [],
    }
    incs = extraer_inconsistencias(datos)
    ret_incs = [i for i in incs if i["tipo"] == "RETENCIONES_INCONSISTENTES"]
    assert len(ret_incs) == 1
    assert ret_incs[0]["diferencia_pct"] == 25.0


def test_ciiu_sin_tipo_basico():
    """CIIU check runs WITHOUT tipo field (simula modo BASICO)."""
    datos = {
        "nit": "9003189639",
        "ciiu_declarado": "4711",
        "ciiu_dian": "4721",
        "tarifa_declarada": 0.008,
        "tarifa_dian": 0.010,
        "declaraciones_ica": [{"periodo": "2024-B1", "base_gravable": 1000000, "tarifa": 0.008, "impuesto": 8000}],
        "exogena_dian": [],
    }
    incs = extraer_inconsistencias(datos)
    ciiu_incs = [i for i in incs if i["tipo"] == "TARIFA_INCORRECTA_CIIU"]
    assert len(ciiu_incs) == 1
    assert ciiu_incs[0]["ciiu_declarado"] == "4711"
    assert ciiu_incs[0]["ciiu_dian"] == "4721"
    assert ciiu_incs[0]["severidad"] == "ALTA"


def test_retenciones_sin_tipo_basico():
    """Retenciones check runs WITHOUT tipo field (simula modo BASICO)."""
    datos = {
        "nit": "9003189639",
        "diferencia_pct": 25.0,
        "retenciones_declaradas_practicadas": 500000,
        "retenciones_exogena_practicadas": 750000,
        "declaraciones_ica": [{"periodo": "2024-B1", "base_gravable": 1000000, "tarifa": 0.008, "impuesto": 8000}],
        "exogena_dian": [],
    }
    incs = extraer_inconsistencias(datos)
    ret_incs = [i for i in incs if i["tipo"] == "RETENCIONES_INCONSISTENTES"]
    assert len(ret_incs) == 1
    assert ret_incs[0]["diferencia_pct"] == 25.0
    assert ret_incs[0]["retenciones_declaradas_practicadas"] == 500000
    assert ret_incs[0]["retenciones_exogena_practicadas"] == 750000
    assert ret_incs[0]["severidad"] == "ALTA"


def test_ciiu_sin_diferencia_tarifa_no_genera_inconsistencia():
    """CIIU mismatch but tarifa_dian <= tarifa_declarada: no inconsistency."""
    datos = {
        "nit": "9003189639",
        "ciiu_declarado": "4711",
        "ciiu_dian": "4721",
        "tarifa_declarada": 0.010,
        "tarifa_dian": 0.008,
        "declaraciones_ica": [{"periodo": "2024-B1", "base_gravable": 1000000, "tarifa": 0.008, "impuesto": 8000}],
        "exogena_dian": [],
    }
    incs = extraer_inconsistencias(datos)
    ciiu_incs = [i for i in incs if i["tipo"] == "TARIFA_INCORRECTA_CIIU"]
    assert len(ciiu_incs) == 0


def test_retenciones_sin_diferencia_no_genera_inconsistencia():
    """Retenciones data present but diff_pct is 0: no inconsistency."""
    datos = {
        "nit": "9003189639",
        "diferencia_pct": 0,
        "retenciones_declaradas_practicadas": 500000,
        "retenciones_exogena_practicadas": 500000,
        "declaraciones_ica": [{"periodo": "2024-B1", "base_gravable": 1000000, "tarifa": 0.008, "impuesto": 8000}],
        "exogena_dian": [],
    }
    incs = extraer_inconsistencias(datos)
    ret_incs = [i for i in incs if i["tipo"] == "RETENCIONES_INCONSISTENTES"]
    assert len(ret_incs) == 0
