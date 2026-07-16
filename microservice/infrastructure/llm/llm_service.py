import asyncio
import logging
import time

from config import settings
from domain.errors import LLMRateLimitError
from domain.ports.llm_port import LLMProvider
from infrastructure.llm.anthropic_provider import AnthropicProvider
from infrastructure.llm.huggingface_provider import HuggingFaceProvider
from infrastructure.llm.nvidia_nim_provider import NvidiaNIMProvider
from infrastructure.llm.openai_provider import OpenAIProvider
from tasks.retry import with_retry

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        self.providers: list[LLMProvider] = []
        self._init_providers()
        self._last_call_time = 0.0
        self._min_interval = 60.0 / (settings.llm_rate_limit_rpm or 40)

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

            # Descubrimiento automático si no hay modelo configurado
            if not getattr(p, "model", None) and hasattr(p, "discover_models"):
                try:
                    models = await p.discover_models()
                    if models:
                        logger.info(
                            "LLM: %s descubrió %d modelos disponibles",
                            type(p).__name__, len(models),
                        )
                        p.model = models[0]
                        logger.info("LLM: %s seleccionó modelo: %s", type(p).__name__, p.model)
                    else:
                        logger.warning("LLM: %s no descubrió modelos", type(p).__name__)
                except Exception as e:
                    logger.warning("LLM: %s fallo en descubrimiento: %s", type(p).__name__, e)

        if not self.providers:
            logger.warning("No hay providers LLM configurados — modo degradado permanente")

    async def _throttle(self):
        now = time.time()
        elapsed = now - self._last_call_time
        if elapsed < self._min_interval:
            await asyncio.sleep(self._min_interval - elapsed)
        self._last_call_time = time.time()

    async def _call_provider(self, provider: LLMProvider, messages: list[dict], schema: dict | None) -> dict:
        await self._throttle()
        return await with_retry(
            provider.chat_json, messages, schema,
            max_attempts=settings.retry_max_attempts,
            retry_on=(LLMRateLimitError,),
        )

    async def analyze(self, messages: list[dict], schema: dict | None = None) -> dict:
        ultimo_error = "No hay providers configurados"

        for provider in self.providers:
            try:
                logger.info("LLM: intentando con %s", provider.__class__.__name__)
                return await self._call_provider(provider, messages, schema)
            except LLMRateLimitError as e:
                logger.warning(
                    "LLM: %s rate limit excedido — probando siguiente provider: %s",
                    provider.__class__.__name__, str(e),
                )
                ultimo_error = str(e)
                continue
            except Exception as e:
                error_str = str(e)
                if "DEGRADED" in error_str:
                    error_short = "función degradada (400)"
                elif "timed out" in error_str.lower() or "timeout" in error_str.lower():
                    error_short = "timeout"
                elif "Connection" in error_str and "error" in error_str.lower():
                    error_short = "error de conexión"
                elif "rate limit" in error_str.lower() or "429" in error_str:
                    error_short = "rate limit"
                elif len(error_str) > 80:
                    error_short = error_str[:80] + "..."
                else:
                    error_short = error_str
                logger.warning("LLM: %s falló: %s", provider.__class__.__name__, error_short)
                ultimo_error = error_short
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
