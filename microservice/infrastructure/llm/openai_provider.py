import json
import logging

from config import settings
from domain.ports.llm_port import LLMProvider, LLMResponse
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.llm_tier1_api_key)
        self.model = "gpt-4o"

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
            provider="openai",
        )

    async def chat_json(self, messages: list[dict], schema: dict | None = None) -> dict:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=settings.llm_max_tokens,
            temperature=0.1,
            timeout=settings.llm_timeout,
        )

        text = response.choices[0].message.content or "{}"
        try:
            inicio = text.index("{")
            fin = text.rindex("}") + 1
            return json.loads(text[inicio:fin])
        except (ValueError, json.JSONDecodeError) as e:
            logger.warning("Error parseando respuesta OpenAI: %s", str(e))
            return {"explicacion": text, "hallazgos_enriquecidos": []}
