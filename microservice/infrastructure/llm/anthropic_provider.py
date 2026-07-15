import json
import logging

import anthropic
from config import settings
from domain.ports.llm_port import LLMProvider, LLMResponse

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
            timeout=kwargs.get("timeout", settings.llm_timeout or None),
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
            timeout=settings.llm_timeout or None,
        )

        text = response.content[0].text if response.content else "{}"
        tokens_in = _safe_int(response, 'usage', 'input_tokens')
        tokens_out = _safe_int(response, 'usage', 'output_tokens')
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
            logger.warning("Error parseando respuesta Anthropic: %s", str(e))
            return {"explicacion": text, "hallazgos_enriquecidos": [],
                    "tokens_entrada": tokens_in, "tokens_salida": tokens_out}
