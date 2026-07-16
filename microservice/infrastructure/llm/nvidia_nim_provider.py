import json
import logging
import re

from config import settings
from domain.errors import LLMRateLimitError
from domain.ports.llm_port import LLMProvider, LLMResponse
from openai import AsyncOpenAI
from openai import RateLimitError as OpenAIRateLimitError

logger = logging.getLogger(__name__)


async def _fetch_available_models(client) -> list[str]:
    """Consulta /v1/models para obtener lista de modelos disponibles."""
    try:
        response = await client.models.list()
        return [m.id for m in response.data if hasattr(m, "id")]
    except Exception as e:
        logger.warning("NVIDIA: error consultando modelos disponibles: %s", str(e)[:100])
        return []


def _clean_explanacion(text: str) -> str:
    text = text.strip()
    if re.match(r"^```", text):
        lines = text.split("\n")
        if lines[-1].strip() == "```":
            text = "\n".join(lines[1:-1])
        else:
            text = "\n".join(lines[1:])
        text = text.strip()
    text = re.sub(r'```json\s*\{.*?\}\s*```', '', text, flags=re.DOTALL)
    text = re.sub(r'```\s*\{.*?\}\s*```', '', text, flags=re.DOTALL)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


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


AVAILABLE_MODELS: list[str] | None = None
SELECTED_MODEL: str | None = None

PREFERRED_MODELS = [
    "meta/llama-3.1-8b-instruct",
    "mistralai/mixtral-8x7b-instruct-v0.1",
    "qwen/qwen3.5-122b-a10b",
    "mistralai/mistral-7b-instruct-v0.3",
    "google/gemma-3-12b-it",
    "mistralai/mistral-large",
    "meta/llama-3.3-70b-instruct",
]


async def _verify_model(client: AsyncOpenAI, model: str) -> bool:
    try:
        await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "test"}],
            max_tokens=1,
            timeout=10,
        )
        return True
    except Exception:
        return False


async def _auto_select_model() -> str:
    global SELECTED_MODEL
    if SELECTED_MODEL is not None:
        return SELECTED_MODEL

    client = AsyncOpenAI(
        api_key=settings.llm_tier2_api_key,
        base_url=settings.llm_tier2_api_base or "https://integrate.api.nvidia.com/v1",
    )

    configured = settings.llm_tier2_model
    if configured:
        if await _verify_model(client, configured):
            logger.info("NVIDIA: modelo configurado %s funciona", configured)
            SELECTED_MODEL = configured
            return configured
        logger.warning("NVIDIA: modelo %s NO disponible, buscando alternativas...", configured)
    else:
        logger.info("NVIDIA: sin modelo configurado, buscando entre modelos preferidos...")
    for model in PREFERRED_MODELS:
        if await _verify_model(client, model):
            logger.info("NVIDIA: seleccionado automaticamente: %s", model)
            SELECTED_MODEL = model
            return model

    logger.warning("NVIDIA: ningun modelo preferido funciona, usando configurado: %s", configured)
    SELECTED_MODEL = configured
    return configured


class NvidiaNIMProvider(LLMProvider):
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.llm_tier2_api_key,
            base_url=settings.llm_tier2_api_base or "https://integrate.api.nvidia.com/v1",
        )
        self._model_resolved = False
        self.model = settings.llm_tier2_model

    async def discover_models(self) -> list[str]:
        client = AsyncOpenAI(
            api_key=settings.llm_tier2_api_key,
            base_url=settings.llm_tier2_api_base or "https://integrate.api.nvidia.com/v1",
        )
        return await _fetch_available_models(client)

    async def _ensure_model(self):
        if not self._model_resolved:
            self.model = await _auto_select_model()
            self._model_resolved = True

    async def chat(self, messages: list[dict], **kwargs) -> LLMResponse:
        await self._ensure_model()
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=kwargs.get("max_tokens", settings.llm_max_tokens),
                temperature=kwargs.get("temperature", 0.1),
                timeout=kwargs.get("timeout", settings.llm_timeout),
            )
        except OpenAIRateLimitError as e:
            raise LLMRateLimitError(str(e))

        return LLMResponse(
            content=response.choices[0].message.content or "",
            tokens_entrada=response.usage.prompt_tokens if response.usage else 0,
            tokens_salida=response.usage.completion_tokens if response.usage else 0,
            modelo=self.model,
            provider="nvidia_nim",
        )

    async def chat_json(self, messages: list[dict], schema: dict | None = None) -> dict:
        await self._ensure_model()
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=settings.llm_max_tokens,
                temperature=0.1,
                timeout=settings.llm_timeout or None,
            )
        except OpenAIRateLimitError as e:
            raise LLMRateLimitError(str(e))

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
        except (ValueError, json.JSONDecodeError):
            logger.warning("Respuesta Nvidia NIM sin JSON válido — usando texto plano")
            return {"explicacion": _clean_explanacion(text), "hallazgos_enriquecidos": [],
                    "tokens_entrada": tokens_in, "tokens_salida": tokens_out}
