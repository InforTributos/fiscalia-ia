import json
import logging

from config import settings
from domain.ports.llm_port import LLMProvider, LLMResponse
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


def _safe_int(obj, *attrs):
    try:
        val = obj
        for a in attrs:
            val = getattr(val, a)
        if not isinstance(val, (int, float)):
            return 0
        return int(val)
    except (AttributeError, TypeError, ValueError):
        return 0


class HuggingFaceProvider(LLMProvider):
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.llm_tier3_api_key,
            base_url=settings.llm_tier3_api_base or "https://api-inference.huggingface.co/v1",
        )
        self.model = settings.llm_tier3_model

    async def chat(self, messages: list[dict], **kwargs) -> LLMResponse:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=kwargs.get("max_tokens", settings.llm_max_tokens),
            temperature=kwargs.get("temperature", 0.1),
            timeout=kwargs.get("timeout", settings.llm_timeout),
        )

        return LLMResponse(
            content=response.choices[0].message.content or "",
            tokens_entrada=response.usage.prompt_tokens if response.usage else 0,
            tokens_salida=response.usage.completion_tokens if response.usage else 0,
            modelo=self.model,
            provider="huggingface",
        )

    async def chat_json(self, messages: list[dict], schema: dict | None = None) -> dict:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=settings.llm_max_tokens,
            temperature=0.1,
            timeout=settings.llm_timeout or None,
        )

        text = response.choices[0].message.content or "{}"
        tokens_in = _safe_int(response, 'usage', 'prompt_tokens')
        tokens_out = _safe_int(response, 'usage', 'completion_tokens')
        try:
            inicio = text.index("{")
            decoder = json.JSONDecoder()
            data, _ = decoder.raw_decode(text, inicio)
            if isinstance(data, list):
                data = data[0] if data else {}
            result = data if isinstance(data, dict) else {"explicacion": str(data)}
            result.setdefault("tokens_entrada", tokens_in)
            result.setdefault("tokens_salida", tokens_out)
            return result
        except (ValueError, json.JSONDecodeError) as e:
            logger.warning("Error parseando respuesta HuggingFace: %s", str(e))
            return {"explicacion": text, "hallazgos_enriquecidos": [],
                    "tokens_entrada": tokens_in, "tokens_salida": tokens_out}
