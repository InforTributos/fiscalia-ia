import logging

import litellm
from config import settings
from domain.ports.llm_port import LLMPort
from litellm import Router
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from infrastructure.adapters.llm.prompts import Prompts

logger = logging.getLogger(__name__)


class LiteLLMAdapter(LLMPort):
    def __init__(self):
        model_list = []

        model_list.append(
            {
                "model_name": "primary",
                "litellm_params": {
                    "model": f"{settings.llm_primary_provider}/{settings.llm_primary_model}",
                    "api_key": settings.llm_primary_api_key,
                    "temperature": 0.1,
                    "timeout": settings.llm_timeout,
                },
            }
        )
        if settings.llm_primary_api_base:
            model_list[-1]["litellm_params"]["api_base"] = settings.llm_primary_api_base

        if settings.llm_mode == "primary_fallback" and settings.llm_fallback_provider:
            model_list.append(
                {
                    "model_name": "fallback",
                    "litellm_params": {
                        "model": f"{settings.llm_fallback_provider}/{settings.llm_fallback_model}",
                        "api_key": settings.llm_fallback_api_key,
                        "temperature": 0.1,
                        "timeout": settings.llm_timeout,
                    },
                }
            )

        fallbacks = [{"primary": ["fallback"]}] if len(model_list) > 1 else []
        self.router = Router(model_list=model_list, fallbacks=fallbacks)
        self.prompts = Prompts()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception_type((litellm.APIError, litellm.Timeout, litellm.RateLimitError)),
    )
    async def analizar(self, contexto: dict) -> dict:
        prompt = self.prompts.construir(contexto)
        logger.info(
            "LiteLLM: enviando análisis tipo %s a %s/%s",
            contexto.get("tipo", "desconocido"),
            settings.llm_primary_provider,
            settings.llm_primary_model,
        )

        try:
            response = await self.router.acompletion(
                model="primary",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Eres un asistente especializado en fiscalización del Impuesto "
                            "de Industria y Comercio (ICA) en Colombia. Respondes exclusivamente "
                            "basado en los datos proporcionados, sin inventar información."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=settings.llm_max_tokens,
            )

            resultado = self.prompts.parsear_respuesta(response.choices[0].message.content)
            resultado["tokens_entrada"] = getattr(response.usage, "prompt_tokens", 0)
            resultado["tokens_salida"] = getattr(response.usage, "completion_tokens", 0)
            logger.info(
                "LiteLLM: análisis completado (%d tokens)",
                resultado.get("tokens_entrada", 0) + resultado.get("tokens_salida", 0),
            )
            return resultado

        except Exception as e:
            logger.warning("Primary falló, intentando fallback: %s", str(e))
            if settings.llm_mode == "primary_fallback" and settings.llm_fallback_provider:
                try:
                    response = await self.router.acompletion(
                        model="fallback",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=settings.llm_max_tokens,
                    )
                    resultado = self.prompts.parsear_respuesta(response.choices[0].message.content)
                    resultado["tokens_entrada"] = getattr(response.usage, "prompt_tokens", 0)
                    resultado["tokens_salida"] = getattr(response.usage, "completion_tokens", 0)
                    return resultado
                except Exception as fallback_err:
                    logger.error("Fallback también falló: %s", str(fallback_err))
                    return self._respuesta_degradada()
            return self._respuesta_degradada()

    def _respuesta_degradada(self) -> dict:
        return {
            "explicacion": (
                "El análisis con IA no está disponible en este momento. "
                "Los cruces e inconsistencias se presentan sin generación de lenguaje natural."
            ),
            "hallazgos_enriquecidos": [],
            "modo_degradado": True,
            "tokens_entrada": 0,
            "tokens_salida": 0,
        }
