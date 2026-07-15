from domain.fiscalizacion.agent_reviewer import (
    fusionar_revision_ia,
    revisar_hallazgo_deterministico,
)


def test_revisar_completo_con_evidencia_directa():
    hallazgo = {
        "evidencias": [{"fuente": "DIAN"}],
        "fuerza_probatoria": "DIRECTA",
        "score": 85,
        "accionable": True,
        "brecha_valor": 1000000,
        "impuesto_estimado": 500000,
        "resumen": "Discrepancia detectada",
    }
    result = revisar_hallazgo_deterministico(hallazgo)
    assert result["completitud"] >= 80
    assert result["estado_revision"] == "COMPLETO"
    assert result["accion_recomendada"] == "Pasar a revision humana prioritaria."


def test_revisar_sin_evidencia_ni_resumen():
    hallazgo = {
        "fuerza_probatoria": "DIRECTA",
        "score": 85,
        "accionable": True,
        "brecha_valor": 1000000,
        "impuesto_estimado": 500000,
    }
    result = revisar_hallazgo_deterministico(hallazgo)
    assert result["completitud"] <= 65
    assert "evidencia(s)" in result["evidencia_faltante"][0]


def test_revisar_no_accionable():
    hallazgo = {
        "evidencias": [{"fuente": "DIAN"}],
        "fuerza_probatoria": "DIRECTA",
        "score": 85,
        "accionable": False,
        "brecha_valor": 1000000,
        "impuesto_estimado": 500000,
        "resumen": "test",
    }
    result = revisar_hallazgo_deterministico(hallazgo)
    assert any("ventana legal" in r for r in result["riesgos"])


def test_revisar_brecha_cero():
    hallazgo = {
        "evidencias": [{"fuente": "DIAN"}],
        "fuerza_probatoria": "DIRECTA",
        "score": 80,
        "accionable": True,
        "brecha_valor": 0,
        "impuesto_estimado": 0,
        "resumen": "test",
    }
    result = revisar_hallazgo_deterministico(hallazgo)
    assert any("Cuantificar" in f for f in result["evidencia_faltante"])


def test_revisar_indiciaria():
    hallazgo = {
        "evidencias": [{"fuente": "DIAN"}, {"fuente": "RUES"}],
        "fuerza_probatoria": "INDICIARIA",
        "score": 70,
        "accionable": True,
        "brecha_valor": 500000,
        "impuesto_estimado": 100000,
        "resumen": "test",
    }
    result = revisar_hallazgo_deterministico(hallazgo)
    assert any("indiciario" in r.lower() for r in result["riesgos"])
    assert len(result["preguntas"]) >= 1


def test_revisar_score_alto_sin_evidencia():
    hallazgo = {
        "fuerza_probatoria": "MEDIA",
        "score": 90,
        "accionable": True,
        "brecha_valor": 1000000,
        "impuesto_estimado": 500000,
    }
    result = revisar_hallazgo_deterministico(hallazgo)
    assert any("Score alto sin evidencia" in r for r in result["riesgos"])


def test_revisar_fuerza_directa_requiere_1_evidencia():
    hallazgo = {
        "evidencias": [{"fuente": "DIAN"}],
        "fuerza_probatoria": "DIRECTA",
        "score": 60,
        "accionable": True,
        "brecha_valor": 100000,
        "impuesto_estimado": 50000,
        "resumen": "test",
    }
    result = revisar_hallazgo_deterministico(hallazgo)
    assert result["completitud"] >= 80


def test_revisar_fuerza_media_requiere_2_evidencias():
    hallazgo = {
        "evidencias": [{"fuente": "DIAN"}],
        "fuerza_probatoria": "MEDIA",
        "score": 60,
        "accionable": True,
        "brecha_valor": 100000,
        "impuesto_estimado": 50000,
        "resumen": "test",
    }
    result = revisar_hallazgo_deterministico(hallazgo)
    assert any("evidencia(s)" in f for f in result["evidencia_faltante"])


def test_revisar_incompleto():
    hallazgo = {
        "fuerza_probatoria": "DIRECTA",
        "score": 0,
        "accionable": False,
    }
    result = revisar_hallazgo_deterministico(hallazgo)
    assert result["estado_revision"] == "INCOMPLETO"


def test_fusionar_ia_normal():
    base = {"agente": "revisor_hallazgos", "completitud": 85}
    ia = {"comentario": "Se requiere mas documentacion", "riesgos": ["Riesgo A"], "preguntas": ["Pregunta 1"]}
    result = fusionar_revision_ia(base, ia)
    assert result["ia_disponible"] is True
    assert result["comentario_ia"] == "Se requiere mas documentacion"
    assert result["riesgos_ia"] == ["Riesgo A"]
    assert result["preguntas_ia"] == ["Pregunta 1"]


def test_fusionar_ia_degradado():
    base = {"agente": "revisor_hallazgos", "completitud": 85}
    ia = {"modo_degradado": True, "error": "LLM timeout"}
    result = fusionar_revision_ia(base, ia)
    assert result["ia_disponible"] is False
    assert result["ia_error"] == "LLM timeout"
    assert "ia_disponible" not in ia
    assert "ia_error" not in ia


def test_fusionar_ia_usar_explicacion_si_no_hay_comentario():
    base = {"agente": "revisor_hallazgos"}
    ia = {"explicacion": "Explicacion directa"}
    result = fusionar_revision_ia(base, ia)
    assert result["comentario_ia"] == "Explicacion directa"
