from infrastructure.llm.prompts import construir_prompt, parsear_respuesta


def test_prompt_omiso_incluye_nit():
    prompt = construir_prompt("omiso", datos_fiscales="{}")
    assert "omiso" in prompt.lower()


def test_prompt_inexacto_incluye_datos():
    prompt = construir_prompt(
        "inexacto",
        datos_fiscales='{"nit": "test"}',
        inconsistencias="[]",
        srf_total="50",
    )
    assert "inconsistencias" in prompt.lower()
    assert "50" in prompt


def test_prompt_srf_incluye_score():
    prompt = construir_prompt("srf", srf_total="75", factores='[{"nombre": "test", "valor": 30}]')
    assert "75" in prompt


def test_prompt_clasificacion_incluye_datos():
    prompt = construir_prompt("clasificacion", datos_mcp='{"nit": "test"}')
    assert "clasificacion" in prompt.lower()


def test_parsear_respuesta_json():
    parsed = parsear_respuesta('{"explicacion": "test", "score": 50}')
    assert parsed["explicacion"] == "test"
    assert parsed["score"] == 50


def test_parsear_respuesta_sin_json():
    parsed = parsear_respuesta("Respuesta sin JSON")
    assert parsed["explicacion"] == "Respuesta sin JSON"
    assert parsed["hallazgos_enriquecidos"] == []
