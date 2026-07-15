from domain.fiscalizacion.rule_engine import evaluar_reglas


def test_r2_presencia_sin_declaracion():
    perfil = {
        "nit": "9003189639",
        "periodo": "2024",
        "presencia_registral": True,
        "senales_actividad": ["facturacion electronica"],
        "base_presuntiva": 500000000,
        "impuesto_presuntivo": 5000000,
    }
    result = evaluar_reglas(perfil, ["R2"])
    assert len(result) == 1
    assert result[0]["tipo_hallazgo"] == "OMISO"
    assert result[0]["regla"] == "R2"


def test_r2_sin_presencia_ni_senales():
    perfil = {"nit": "9003189639", "periodo": "2024"}
    result = evaluar_reglas(perfil, ["R2"])
    assert result == []


def test_r2_con_declaracion():
    perfil = {
        "nit": "9003189639",
        "periodo": "2024",
        "declaraciones_ica": [{"base_gravable": 100000}],
    }
    result = evaluar_reglas(perfil, ["R2"])
    assert result == []


def test_r4_facturacion_sin_declaracion():
    perfil = {
        "nit": "9003189639",
        "periodo": "2024",
        "facturacion_electronica": [{"valor": 1000000}],
    }
    result = evaluar_reglas(perfil, ["R4"])
    assert len(result) == 1
    assert result[0]["tipo_hallazgo"] == "OMISO"


def test_r4_base_menor_que_facturacion():
    perfil = {
        "nit": "9003189639",
        "periodo": "2024",
        "facturacion_electronica": [{"valor": 1000000}],
        "declaraciones_ica": [{"base_gravable": 500000}],
    }
    result = evaluar_reglas(perfil, ["R4"])
    assert len(result) == 1
    assert result[0]["tipo_hallazgo"] == "INEXACTO"


def test_r4_facturacion_cero():
    perfil = {"nit": "9003189639", "periodo": "2024", "facturacion_electronica": []}
    result = evaluar_reglas(perfil, ["R4"])
    assert result == []


def test_r5_contratos_sin_declaracion():
    perfil = {
        "nit": "9003189639",
        "periodo": "2024",
        "contratos_publicos": [{"valor": 2000000}],
    }
    result = evaluar_reglas(perfil, ["R5"])
    assert len(result) == 1
    assert result[0]["tipo_hallazgo"] == "OMISO"


def test_r5_contratos_mayores_base():
    perfil = {
        "nit": "9003189639",
        "periodo": "2024",
        "contratos_publicos": [{"valor": 2000000}],
        "declaraciones_ica": [{"base_gravable": 1000000}],
    }
    result = evaluar_reglas(perfil, ["R5"])
    assert len(result) == 1
    assert result[0]["tipo_hallazgo"] == "INEXACTO"


def test_r5_sin_contratos():
    perfil = {"nit": "9003189639", "periodo": "2024", "contratos_publicos": []}
    result = evaluar_reglas(perfil, ["R5"])
    assert result == []


def test_r6_declaraciones_cero_con_senales():
    perfil = {
        "nit": "9003189639",
        "periodo": "2024",
        "declaraciones_ica": [{"base_gravable": 0}, {"base_gravable": 0}, {"base_gravable": 50000}],
        "senales_actividad": ["electricidad"],
    }
    result = evaluar_reglas(perfil, ["R6"])
    assert len(result) == 1
    assert result[0]["tipo_hallazgo"] == "INEXACTO_INDICIARIO"


def test_r6_sin_declaraciones():
    perfil = {"nit": "9003189639", "periodo": "2024"}
    result = evaluar_reglas(perfil, ["R6"])
    assert result == []


def test_r6_ceros_insuficientes():
    perfil = {
        "nit": "9003189639",
        "periodo": "2024",
        "declaraciones_ica": [{"base_gravable": 0}],
    }
    result = evaluar_reglas(perfil, ["R6"])
    assert result == []


def test_r7_tarifa_declarada_menor():
    perfil = {
        "nit": "9003189639",
        "periodo": "2024",
        "tarifa_declarada": 0.005,
        "tarifa_correcta": 0.01,
        "declaraciones_ica": [{"base_gravable": 100000000}],
    }
    result = evaluar_reglas(perfil, ["R7"])
    assert len(result) == 1
    assert result[0]["tipo_hallazgo"] == "INEXACTO"


def test_r7_tarifa_correcta_igual():
    perfil = {
        "nit": "9003189639",
        "periodo": "2024",
        "tarifa_declarada": 0.01,
        "tarifa_correcta": 0.01,
        "declaraciones_ica": [{"base_gravable": 100000000}],
    }
    result = evaluar_reglas(perfil, ["R7"])
    assert result == []


def test_r7_sin_base():
    perfil = {
        "nit": "9003189639",
        "periodo": "2024",
        "tarifa_declarada": 0.005,
        "tarifa_correcta": 0.01,
    }
    result = evaluar_reglas(perfil, ["R7"])
    assert result == []


def test_r8_atipico_sectorial():
    perfil = {
        "nit": "9003189639",
        "periodo": "2024",
        "atipico_sectorial": True,
        "indicadores_sectoriales": {},
    }
    result = evaluar_reglas(perfil, ["R8"])
    assert len(result) == 1


def test_r8_percentiles_bajos():
    perfil = {
        "nit": "9003189639",
        "periodo": "2024",
        "indicadores_sectoriales": {
            "margen": {"percentil": 5},
            "rotacion": {"percentil": 8},
        },
    }
    result = evaluar_reglas(perfil, ["R8"])
    assert len(result) == 1


def test_r8_sin_indicadores():
    perfil = {"nit": "9003189639", "periodo": "2024"}
    result = evaluar_reglas(perfil, ["R8"])
    assert result == []


def test_r9_ingresos_no_declarados():
    perfil = {
        "nit": "9003189639",
        "periodo": "2024",
        "ingresos_locales_no_declarados": 50000000,
        "evidencia_territorialidad": {"municipio": "001"},
    }
    result = evaluar_reglas(perfil, ["R9"])
    assert len(result) == 1
    assert result[0]["tipo_hallazgo"] == "INEXACTO"


def test_r9_sin_ingresos():
    perfil = {"nit": "9003189639", "periodo": "2024"}
    result = evaluar_reglas(perfil, ["R9"])
    assert result == []


def test_r10_caida_abrupta():
    perfil = {
        "nit": "9003189639",
        "periodo": "2024",
        "historico_bases": [
            {"periodo": "2023", "base_gravable": 100000000},
            {"periodo": "2024", "base_gravable": 10000000},
        ],
    }
    result = evaluar_reglas(perfil, ["R10"])
    assert len(result) == 1
    assert result[0]["tipo_hallazgo"] == "INEXACTO_INDICIARIO"


def test_r10_sin_historico_suficiente():
    perfil = {
        "nit": "9003189639",
        "periodo": "2024",
        "historico_bases": [{"periodo": "2024", "base_gravable": 50000000}],
    }
    result = evaluar_reglas(perfil, ["R10"])
    assert result == []


def test_r10_sin_caida_significativa():
    perfil = {
        "nit": "9003189639",
        "periodo": "2024",
        "historico_bases": [
            {"periodo": "2023", "base_gravable": 100000000},
            {"periodo": "2024", "base_gravable": 80000000},
        ],
    }
    result = evaluar_reglas(perfil, ["R10"])
    assert result == []


def test_r1_omiso_sin_declaracion_con_retenciones():
    perfil = {
        "nit": "9003189639",
        "periodo": "2024",
        "retenciones_ica": [{"valor_retenido": 500000}],
        "tarifa_retencion": 0.01,
    }
    result = evaluar_reglas(perfil, ["R1"])
    assert len(result) == 1
    assert result[0]["tipo_hallazgo"] == "OMISO"


def test_r1_sin_retenciones():
    perfil = {"nit": "9003189639", "periodo": "2024", "retenciones_ica": []}
    result = evaluar_reglas(perfil, ["R1"])
    assert result == []


def test_r3_exogena_sin_vinculo_local():
    perfil = {
        "nit": "9003189639",
        "periodo": "2024",
        "exogena_dian": [{"ingresos": 100000000}],
    }
    result = evaluar_reglas(perfil, ["R3"])
    assert result == []


def test_r3_exogena_sin_ingresos():
    perfil = {
        "nit": "9003189639",
        "periodo": "2024",
        "vinculo_local": True,
        "exogena_dian": [],
    }
    result = evaluar_reglas(perfil, ["R3"])
    assert result == []
