from domain.fiscal.unified_score import calcular_score_fiscal_unificado


def test_score_vacio_es_cero():
    result = calcular_score_fiscal_unificado()
    assert result["score_fiscal_unificado"] == 0.0
    assert result["prioridad"] == "BAJA"


def test_score_con_comportamiento_alto():
    analisis = {"score_comportamental": 90, "confianza": 0.9, "hallazgos": []}
    result = calcular_score_fiscal_unificado(analisis_comportamental=analisis)
    assert result["score_fiscal_unificado"] > 25
    assert result["prioridad"] in ("BAJA", "MEDIA", "ALTA", "CRITICA")


def test_score_con_hallazgos_regla_directa():
    reglas = [{"fuerza_probatoria": "DIRECTA", "brecha_valor": 50000000}]
    result = calcular_score_fiscal_unificado(hallazgos_reglas=reglas)
    assert result["score_fiscal_unificado"] > 20


def test_score_max_100():
    analisis = {"score_comportamental": 100, "confianza": 1.0, "hallazgos": [{"tipo": "EXOGENA_CON_DECLARACION_CERO"}]}
    reglas = [{"fuerza_probatoria": "DIRECTA", "brecha_valor": 200000000}]
    temp = [{"tipo": "DESAPARICION_DECLARATIVA", "severidad": "ALTA"}]
    red = {"score_red": 100, "empresas_conectadas": 5}
    result = calcular_score_fiscal_unificado(analisis, red, 100, reglas, temp)
    assert result["score_fiscal_unificado"] <= 100.0
