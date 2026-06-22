import json
import logging

import anthropic
from config import settings
from domain.ports.llm_port import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.llm_tier1_api_key)
        self.model = settings.llm_tier1_model

    async def chat(self, messages: list[dict], **kwargs) -> LLMResponse:
        system = ""
        msgs = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                msgs.append(m)

        response = await self.client.messages.create(
            model=self.model,
            system=system or None,
            messages=msgs,
            max_tokens=kwargs.get("max_tokens", settings.llm_max_tokens),
            temperature=kwargs.get("temperature", 0.1),
            timeout=kwargs.get("timeout", settings.llm_timeout),
        )

        return LLMResponse(
            content=response.content[0].text if response.content else "",
            tokens_entrada=response.usage.input_tokens,
            tokens_salida=response.usage.output_tokens,
            modelo=self.model,
            provider="anthropic",
        )

    async def chat_json(self, messages: list[dict], schema: dict | None = None) -> dict:
        system = ""
        msgs = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                msgs.append(m)

        response = await self.client.messages.create(
            model=self.model,
            system=system or None,
            messages=msgs,
            max_tokens=settings.llm_max_tokens,
            temperature=0.1,
            timeout=settings.llm_timeout,
        )

        text = response.content[0].text if response.content else "{}"
        try:
            inicio = text.index("{")
            fin = text.rindex("}") + 1
            return json.loads(text[inicio:fin])
        except (ValueError, json.JSONDecodeError) as e:
            logger.warning("Error parseando respuesta Anthropic: %s", str(e))
            return {"explicacion": text, "hallazgos_enriquecidos": []}
