from domain.fiscalizacion.rule_engine import evaluar_reglas


def test_r3_exogena_sin_declaracion():
    perfil = {
        "contribuyente_nit": "123", "periodo": "2024",
        "declaraciones_ica": [],
        "exogena_dian": [{"ingresos": 50000000}],
        "vinculo_local": True,
    }
    hallazgos = evaluar_reglas(perfil, reglas=["R3"])
    assert len(hallazgos) == 1
    assert hallazgos[0]["regla"] == "R3"
    assert hallazgos[0]["tipo_hallazgo"] == "OMISO"


def test_r1_retenciones_sin_declaracion():
    perfil = {
        "contribuyente_nit": "123", "periodo": "2024",
        "declaraciones_ica": [],
        "retenciones_ica": [{"valor_retenido": 1000000}],
        "tarifa_retencion": 0.01,
    }
    hallazgos = evaluar_reglas(perfil, reglas=["R1"])
    assert len(hallazgos) == 1
    assert hallazgos[0]["tipo_hallazgo"] == "OMISO"


def test_r10_caida_abrupta():
    perfil = {
        "contribuyente_nit": "123", "periodo": "2024",
        "historico_bases": [
            {"periodo": "2023", "base_gravable": 1000000},
            {"periodo": "2024", "base_gravable": 100000},
        ],
    }
    hallazgos = evaluar_reglas(perfil, reglas=["R10"])
    assert len(hallazgos) == 1
    assert hallazgos[0]["tipo_hallazgo"] == "INEXACTO_INDICIARIO"


def test_perfil_limpio_sin_hallazgos():
    perfil = {
        "contribuyente_nit": "123", "periodo": "2024",
        "declaraciones_ica": [{"base_gravable": 100000, "impuesto": 10000}],
    }
    hallazgos = evaluar_reglas(perfil)
    assert len(hallazgos) == 0
