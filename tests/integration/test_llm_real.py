"""Pruebas de integración real contra NVIDIA NIM.

Ejecutar con:
  PYTHONPATH=microservice pytest tests/integration/test_llm_real.py -v -x
"""

import json

import pytest
from config import settings
from infrastructure.adapters.llm.litellm_adapter import LiteLLMAdapter
from infrastructure.adapters.llm.prompts import Prompts

pytestmark = [
    pytest.mark.integration,
]


@pytest.fixture
def adapter():
    return LiteLLMAdapter()


@pytest.fixture
def prompts():
    return Prompts()


@pytest.fixture
def adapter_fast_fail(monkeypatch):
    """Adapter con timeout bajo para que los fallos rápidos no tarden minutos."""
    monkeypatch.setattr(settings, "llm_timeout", 5)
    return LiteLLMAdapter()


@pytest.mark.asyncio
@pytest.mark.parametrize("tipo", ["analisis_completo", "explicacion_srf"])
async def test_nvidia_nim_respuesta_valida(adapter, prompts, tipo):
    """Llama a NVIDIA NIM real y verifica que la respuesta sea JSON válido."""
    ctx = _contexto_ejemplo(tipo)
    resultado = await adapter.analizar(ctx)

    assert "explicacion" in resultado, (
        f"NVIDIA NIM no retornó 'explicacion': {json.dumps(resultado, indent=2, ensure_ascii=False)}"
    )
    assert len(resultado["explicacion"]) > 20, "Explicación muy corta"
    assert not resultado.get("modo_degradado", False), "Devolvió respuesta degradada"
    assert resultado["tokens_entrada"] > 0, "tokens_entrada debe ser > 0"
    assert resultado["tokens_salida"] > 0, "tokens_salida debe ser > 0"

    print(f"\nNVIDIA NIM ({tipo}): {resultado['tokens_entrada']} in / {resultado['tokens_salida']} out")
    print(f"   Explicacion: {resultado['explicacion'][:200]}...")


@pytest.mark.asyncio
async def test_fallback_nvidia_llama3_2_3b(adapter_fast_fail, prompts):
    """Provoca fallo en primary para probar fallback a NVIDIA llama-3.2-3b.

    Usa adapter_fast_fail (timeout=5s) para que los reintentos del primary
    no extiendan el test a minutos.
    """
    original_key = adapter_fast_fail.router.model_list[0]["litellm_params"]["api_key"]
    try:
        adapter_fast_fail.router.model_list[0]["litellm_params"]["api_key"] = "bad-key-for-testing"
        ctx = _contexto_ejemplo("analisis_completo")
        resultado = await adapter_fast_fail.analizar(ctx)

        assert "explicacion" in resultado
        if resultado.get("modo_degradado"):
            print("Fallback llama-3.2-3b no disponible (rate-limit o error de red)")
        else:
            assert resultado["tokens_entrada"] > 0
            assert resultado["tokens_salida"] > 0
            msg = f"llama-3.2-3b fallback OK: {resultado['tokens_entrada']} in / {resultado['tokens_salida']} out"
            print(msg)
    finally:
        adapter_fast_fail.router.model_list[0]["litellm_params"]["api_key"] = original_key


@pytest.mark.asyncio
async def test_parseo_json_nvidia(adapter, prompts):
    """Verifica que NVIDIA NIM siempre devuelva JSON válido parseable."""
    ctx = _contexto_ejemplo("analisis_completo")
    resultado = await adapter.analizar(ctx)

    assert isinstance(resultado, dict), "Resultado no es dict"
    assert "explicacion" in resultado
    assert "hallazgos_enriquecidos" in resultado, "Falta hallazgos_enriquecidos"

    hallazgos = resultado.get("hallazgos_enriquecidos", [])
    for h in hallazgos:
        assert "explicacion" in h, f"Hallazgo sin explicación: {h}"
        assert "recomendacion" in h, f"Hallazgo sin recomendacion: {h}"


@pytest.mark.asyncio
async def test_consumo_tokens(adapter):
    """Verifica que se reporten tokens de entrada y salida."""
    ctx = _contexto_ejemplo("analisis_completo")
    resultado = await adapter.analizar(ctx)

    assert resultado["tokens_entrada"] > 0
    assert resultado["tokens_salida"] > 0
    total = resultado["tokens_entrada"] + resultado["tokens_salida"]
    print(f"\n✅ Consumo tokens: {resultado['tokens_entrada']} in + {resultado['tokens_salida']} out = {total} total")


def _contexto_ejemplo(tipo: str) -> dict:
    base = {
        "nit": "9003189639",
        "periodo": "2025-01",
    }
    if tipo == "analisis_completo":
        return {
            **base,
            "tipo": "analisis_completo",
            "cruces": [
                {
                    "ciiu": "4711",
                    "ingreso_declarado": 50_000_000,
                    "ingreso_exogena": 120_000_000,
                    "diferencia": 70_000_000,
                    "variacion_pct": 140,
                    "umbral_superado": 1,
                }
            ],
            "inconsistencias": [
                {
                    "tipo_incidencia": "SUBREGISTRO",
                    "ciiu": "4711",
                    "descripcion": "Subdeclaración detectada",
                    "valor_declarado": 50_000_000,
                    "valor_referencia": 120_000_000,
                    "diferencia": 70_000_000,
                    "severidad": "ALTA",
                }
            ],
            "srf": {
                "srf_total": 85,
                "comp_exogena": 35,
                "comp_tarifa": 25,
                "comp_omision": 20,
                "comp_rues": 5,
            },
        }
    elif tipo == "explicacion_srf":
        return {
            **base,
            "tipo": "explicacion_srf",
            "srf": {
                "srf_total": 45,
                "comp_exogena": 15,
                "comp_tarifa": 10,
                "comp_omision": 12,
                "comp_rues": 8,
            },
        }
    return base
