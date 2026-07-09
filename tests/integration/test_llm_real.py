"""Pruebas de integracion real contra LLM providers (Anthropic, OpenAI, NVIDIA NIM).

Ejecutar con:
  PYTHONPATH=microservice pytest tests/integration/test_llm_real.py -v -x -k "not slow"
"""

import json

import pytest
from config import settings
from infrastructure.llm.anthropic_provider import AnthropicProvider
from infrastructure.llm.llm_service import LLMService
from infrastructure.llm.openai_provider import OpenAIProvider
from infrastructure.llm.prompts import construir_prompt

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not settings.llm_tier1_api_key or "changeme" in settings.llm_tier1_api_key,
        reason="Requiere LLM_TIER1_API_KEY real en .env",
    ),
]


@pytest.fixture
def llm_service():
    return LLMService()


@pytest.mark.asyncio
async def test_anthropic_respuesta_valida(llm_service):
    """Llama a Anthropic Claude real y verifica respuesta valida."""
    messages = [
        {"role": "system", "content": "Eres un asistente experto en fiscalizacion del ICA en Colombia."},
        {"role": "user", "content": construir_prompt(
            "explicacion_srf",
            datos_fiscales=json.dumps(_datos_ejemplo(), indent=2, ensure_ascii=False),
            inconsistencias=json.dumps([], indent=2, ensure_ascii=False),
            srf_total="45.0",
        )},
    ]
    resultado = await llm_service.analyze(messages)

    assert "explicacion" in resultado or "respuesta_plana" in resultado, (
        f"Anthropic no retorno explicacion: {json.dumps(resultado, indent=2, ensure_ascii=False)}"
    )
    texto = resultado.get("explicacion", resultado.get("respuesta_plana", ""))
    assert len(texto) > 20, "Explicacion muy corta"


@pytest.mark.asyncio
async def test_fallback_providers(llm_service, monkeypatch):
    """Provoca fallo en Tier 1 para probar fallback a Tier 2/3."""
    monkeypatch.setattr(settings, "llm_tier1_api_key", "sk-bad-key-for-testing")
    messages = [
        {"role": "system", "content": "Eres un asistente experto."},
        {"role": "user", "content": "Responde brevemente: que es el ICA?"},
    ]
    resultado = await llm_service.analyze(messages)

    assert "explicacion" in resultado or "respuesta_plana" in resultado
    texto = resultado.get("explicacion", resultado.get("respuesta_plana", ""))
    assert len(texto) > 10
    print(f"\nFallback OK: {resultado.get('provider', 'unknown')}")


@pytest.mark.asyncio
async def test_openai_respuesta_valida():
    """Llama a OpenAI GPT real si esta configurado."""
    if not settings.llm_tier1_api_key or "openai" not in (settings.llm_tier1_provider or ""):
        pytest.skip("LLM_TIER1_PROVIDER no es openai")
    provider = OpenAIProvider()
    messages = [
        {"role": "system", "content": "Eres un asistente experto en fiscalizacion."},
        {"role": "user", "content": "Explica brevemente el SRF en el contexto del ICA."},
    ]
    resultado = await provider.analyze(messages)
    assert len(resultado.get("respuesta_plana", "")) > 20


@pytest.mark.asyncio
async def test_anthropic_provider_directo():
    """Verifica AnthropicProvider directamente (sin fallback)."""
    if settings.llm_tier1_provider and settings.llm_tier1_provider != "anthropic":
        pytest.skip("LLM_TIER1_PROVIDER no es anthropic")
    provider = AnthropicProvider()
    messages = [
        {"role": "user", "content": "Responde solo 'OK' si recibes este mensaje."},
    ]
    resultado = await provider.analyze(messages)
    texto = resultado.get("respuesta_plana", "")
    assert "OK" in texto


def _datos_ejemplo() -> dict:
    return {
        "nit": "9003189639",
        "razon_social": "EMPRESA EJEMPLO SAS",
        "ciiu": "4711",
        "regimen": "COMUN",
        "declaraciones_ica": [
            {"periodo": "2024", "base_gravable": 50000000, "impuesto": 3500000, "vlor_pago": 3500000},
        ],
        "exogena_dian": [
            {"periodo": "2024", "ingresos": 120000000},
        ],
        "rues_estado": "",
    }
