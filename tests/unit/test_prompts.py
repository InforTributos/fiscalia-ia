from infrastructure.adapters.llm.prompts import Prompts


def test_prompt_analisis_incluye_nit_y_periodo():
    prompts = Prompts()
    ctx = {
        "tipo": "analisis_completo",
        "nit": "9003189639",
        "periodo": "2025-01",
        "cruces": [],
        "inconsistencias": [],
        "srf": {"srf_total": 50},
    }
    prompt = prompts.construir(ctx)
    assert "9003189639" in prompt
    assert "2025-01" in prompt


def test_prompt_score_incluye_srf():
    prompts = Prompts()
    ctx = {"tipo": "explicacion_srf", "nit": "9003189639", "periodo": "2025-01", "srf": {"srf_total": 85}}
    prompt = prompts.construir(ctx)
    assert "85" in prompt
    assert "explica" in prompt


def test_parsear_respuesta_json():
    prompts = Prompts()
    texto = '{"explicacion": "test", "hallazgos_enriquecidos": []}'
    resultado = prompts.parsear_respuesta(texto)
    assert resultado["explicacion"] == "test"


def test_parsear_respuesta_sin_json():
    prompts = Prompts()
    resultado = prompts.parsear_respuesta("texto sin json")
    assert "explicacion" in resultado
