import logging

from config import settings
from domain.ports.llm_port import LLMProvider
from infrastructure.llm.anthropic_provider import AnthropicProvider
from infrastructure.llm.huggingface_provider import HuggingFaceProvider
from infrastructure.llm.nvidia_nim_provider import NvidiaNIMProvider
from infrastructure.llm.openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        self.providers: list[LLMProvider] = []
        self._init_providers()

    def _init_providers(self):
        if settings.llm_tier1_api_key:
            if settings.llm_tier1_provider == "anthropic":
                self.providers.append(AnthropicProvider())
            elif settings.llm_tier1_provider == "openai":
                self.providers.append(OpenAIProvider())

        if settings.llm_tier2_api_key:
            self.providers.append(NvidiaNIMProvider())

        if settings.llm_tier3_api_key:
            self.providers.append(HuggingFaceProvider())

    async def async_init(self):
        for p in self.providers:
            if hasattr(p, "_ensure_model"):
                try:
                    await p._ensure_model()
                    logger.info("LLM: %s listo (modelo: %s)", type(p).__name__, p.model)
                except Exception as e:
                    logger.warning("LLM: %s fallo en validacion inicial: %s", type(p).__name__, e)

        if not self.providers:
            logger.warning("No hay providers LLM configurados — modo degradado permanente")

    async def _call_provider(self, provider: LLMProvider, messages: list[dict], schema: dict | None) -> dict:
        return await provider.chat_json(messages, schema)

    async def analyze(self, messages: list[dict], schema: dict | None = None) -> dict:
        ultimo_error = "No hay providers configurados"

        for provider in self.providers:
            try:
                logger.info("LLM: intentando con %s", provider.__class__.__name__)
                return await self._call_provider(provider, messages, schema)
            except Exception as e:
                logger.warning("LLM: %s falló: %s", provider.__class__.__name__, str(e))
                ultimo_error = str(e)
                continue

        logger.error("LLM: todos los providers fallaron — retornando respuesta degradada")
        return self._respuesta_degradada(ultimo_error)

    def _respuesta_degradada(self, error: str = "") -> dict:
        return {
            "explicacion": (
                "El análisis con IA no está disponible en este momento. "
                "Los cruces e inconsistencias se presentan sin generación de lenguaje natural."
            ),
            "hallazgos_enriquecidos": [],
            "modo_degradado": True,
            "tokens_entrada": 0,
            "tokens_salida": 0,
            "error": error,
        }

    @property
    def providers_count(self) -> int:
        return len(self.providers)

    @property
    def provider_names(self) -> list[str]:
        return [p.__class__.__name__.replace("Provider", "").lower() for p in self.providers]
