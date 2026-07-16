import json
from unittest.mock import AsyncMock, MagicMock, patch

from infrastructure.llm.anthropic_provider import AnthropicProvider
from infrastructure.llm.huggingface_provider import HuggingFaceProvider
from infrastructure.llm.nvidia_nim_provider import NvidiaNIMProvider
from infrastructure.llm.openai_provider import OpenAIProvider

# ─── Helper factories ─────────────────────────────────────────────────────────

def _mock_anthropic_response(content: str, input_tokens: int = 50, output_tokens: int = 30):
    usage = MagicMock(input_tokens=input_tokens, output_tokens=output_tokens)
    block = MagicMock()
    block.text = content
    response = MagicMock()
    response.content = [block]
    response.usage = usage
    return response


def _mock_openai_response(content: str, prompt_tokens: int = 50, completion_tokens: int = 30):
    usage = MagicMock(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
    choice = MagicMock()
    choice.message.content = content
    response = MagicMock()
    response.choices = [choice]
    response.usage = usage
    return response


def _default_settings(mock_settings):
    mock_settings.llm_tier1_api_key = "sk-test"
    mock_settings.llm_tier1_provider = "anthropic"
    mock_settings.llm_tier1_model = "claude-3-sonnet-20241022"
    mock_settings.llm_tier2_api_key = "nv-test"
    mock_settings.llm_tier2_model = "meta/llama-3.1-8b-instruct"
    mock_settings.llm_tier2_api_base = ""
    mock_settings.llm_tier3_api_key = "hf-test"
    mock_settings.llm_tier3_model = "mistralai/Mistral-7B-Instruct-v0.3"
    mock_settings.llm_tier3_api_base = ""
    mock_settings.llm_max_tokens = 1024
    mock_settings.llm_timeout = 60


# ═══════════════════════════════════════════════════════════════════════════════
# AnthropicProvider
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnthropicProvider:

    @patch("infrastructure.llm.anthropic_provider.settings")
    @patch("infrastructure.llm.anthropic_provider.anthropic.AsyncAnthropic")
    async def test_chat_returns_llm_response(self, mock_anthropic_cls, mock_settings):
        _default_settings(mock_settings)
        mock_response = _mock_anthropic_response("Anthropic reply", 50, 30)
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic_cls.return_value = mock_client

        provider = AnthropicProvider()
        result = await provider.chat([{"role": "user", "content": "Hi"}])

        assert result.content == "Anthropic reply"
        assert result.tokens_entrada == 50
        assert result.tokens_salida == 30
        assert result.provider == "anthropic"

    @patch("infrastructure.llm.anthropic_provider.settings")
    @patch("infrastructure.llm.anthropic_provider.anthropic.AsyncAnthropic")
    async def test_chat_extracts_system_message(self, mock_anthropic_cls, mock_settings):
        _default_settings(mock_settings)
        mock_response = _mock_anthropic_response("OK")
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic_cls.return_value = mock_client

        provider = AnthropicProvider()
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"},
        ]
        await provider.chat(messages)

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["system"] == "You are helpful."
        assert call_kwargs["messages"] == [{"role": "user", "content": "Hello"}]

    @patch("infrastructure.llm.anthropic_provider.settings")
    @patch("infrastructure.llm.anthropic_provider.anthropic.AsyncAnthropic")
    async def test_chat_no_system_message_passes_none(self, mock_anthropic_cls, mock_settings):
        _default_settings(mock_settings)
        mock_response = _mock_anthropic_response("OK")
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic_cls.return_value = mock_client

        provider = AnthropicProvider()
        await provider.chat([{"role": "user", "content": "Hello"}])

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["system"] is None

    @patch("infrastructure.llm.anthropic_provider.settings")
    @patch("infrastructure.llm.anthropic_provider.anthropic.AsyncAnthropic")
    async def test_chat_passes_kwargs(self, mock_anthropic_cls, mock_settings):
        _default_settings(mock_settings)
        mock_response = _mock_anthropic_response("OK")
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic_cls.return_value = mock_client

        provider = AnthropicProvider()
        await provider.chat(
            [{"role": "user", "content": "Hi"}],
            max_tokens=2048, temperature=0.9, timeout=120,
        )

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["max_tokens"] == 2048
        assert call_kwargs["temperature"] == 0.9
        assert call_kwargs["timeout"] == 120

    @patch("infrastructure.llm.anthropic_provider.settings")
    @patch("infrastructure.llm.anthropic_provider.anthropic.AsyncAnthropic")
    async def test_chat_empty_content_returns_empty_string(self, mock_anthropic_cls, mock_settings):
        _default_settings(mock_settings)
        mock_response = MagicMock()
        mock_response.content = []
        mock_response.usage = MagicMock(input_tokens=10, output_tokens=5)
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic_cls.return_value = mock_client

        provider = AnthropicProvider()
        result = await provider.chat([{"role": "user", "content": "Hi"}])
        assert result.content == ""
        assert result.tokens_entrada == 10
        assert result.tokens_salida == 5

    # chat_json ---------------------------------------------------------------

    @patch("infrastructure.llm.anthropic_provider.settings")
    @patch("infrastructure.llm.anthropic_provider.anthropic.AsyncAnthropic")
    async def test_chat_json_returns_parsed_dict(self, mock_anthropic_cls, mock_settings):
        _default_settings(mock_settings)
        text = 'Some preamble {"explicacion": "test", "hallazgos_enriquecidos": []} trailing'
        mock_response = _mock_anthropic_response(text)
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic_cls.return_value = mock_client

        provider = AnthropicProvider()
        result = await provider.chat_json([{"role": "user", "content": "Analyze"}])
        assert result == {"explicacion": "test", "hallazgos_enriquecidos": [], "tokens_entrada": 50, "tokens_salida": 30}

    @patch("infrastructure.llm.anthropic_provider.settings")
    @patch("infrastructure.llm.anthropic_provider.anthropic.AsyncAnthropic")
    async def test_chat_json_invalid_json_returns_fallback(self, mock_anthropic_cls, mock_settings):
        _default_settings(mock_settings)
        mock_response = _mock_anthropic_response("{invalid json}")
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic_cls.return_value = mock_client

        provider = AnthropicProvider()
        result = await provider.chat_json([{"role": "user", "content": "Analyze"}])
        assert result == {"explicacion": "{invalid json}", "hallazgos_enriquecidos": [], "tokens_entrada": 50, "tokens_salida": 30}

    @patch("infrastructure.llm.anthropic_provider.settings")
    @patch("infrastructure.llm.anthropic_provider.anthropic.AsyncAnthropic")
    async def test_chat_json_no_braces_returns_fallback(self, mock_anthropic_cls, mock_settings):
        _default_settings(mock_settings)
        mock_response = _mock_anthropic_response("plain text no json")
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic_cls.return_value = mock_client

        provider = AnthropicProvider()
        result = await provider.chat_json([{"role": "user", "content": "Analyze"}])
        assert result == {"explicacion": "plain text no json", "hallazgos_enriquecidos": [], "tokens_entrada": 50, "tokens_salida": 30}

    @patch("infrastructure.llm.anthropic_provider.settings")
    @patch("infrastructure.llm.anthropic_provider.anthropic.AsyncAnthropic")
    async def test_chat_json_empty_content_returns_empty_dict(self, mock_anthropic_cls, mock_settings):
        _default_settings(mock_settings)
        mock_response = MagicMock()
        mock_response.content = []
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic_cls.return_value = mock_client

        provider = AnthropicProvider()
        result = await provider.chat_json([{"role": "user", "content": "X"}])
        assert result == {"tokens_entrada": 0, "tokens_salida": 0}


# ═══════════════════════════════════════════════════════════════════════════════
# OpenAIProvider
# ═══════════════════════════════════════════════════════════════════════════════

class TestOpenAIProvider:

    @patch("infrastructure.llm.openai_provider.settings")
    @patch("infrastructure.llm.openai_provider.AsyncOpenAI")
    async def test_chat_returns_llm_response(self, mock_openai_cls, mock_settings):
        _default_settings(mock_settings)
        mock_response = _mock_openai_response("OpenAI reply", 60, 20)
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_cls.return_value = mock_client

        provider = OpenAIProvider()
        result = await provider.chat([{"role": "user", "content": "Hi"}])

        assert result.content == "OpenAI reply"
        assert result.tokens_entrada == 60
        assert result.tokens_salida == 20
        assert result.provider == "openai"

    @patch("infrastructure.llm.openai_provider.settings")
    @patch("infrastructure.llm.openai_provider.AsyncOpenAI")
    async def test_chat_passes_kwargs(self, mock_openai_cls, mock_settings):
        _default_settings(mock_settings)
        mock_response = _mock_openai_response("OK")
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_cls.return_value = mock_client

        provider = OpenAIProvider()
        await provider.chat(
            [{"role": "user", "content": "Hi"}],
            max_tokens=512, temperature=0.7, timeout=30,
        )

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["max_tokens"] == 512
        assert call_kwargs["temperature"] == 0.7
        assert call_kwargs["timeout"] == 30

    @patch("infrastructure.llm.openai_provider.settings")
    @patch("infrastructure.llm.openai_provider.AsyncOpenAI")
    async def test_chat_passes_messages_directly(self, mock_openai_cls, mock_settings):
        _default_settings(mock_settings)
        mock_response = _mock_openai_response("OK")
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_cls.return_value = mock_client

        provider = OpenAIProvider()
        messages = [{"role": "system", "content": "Be helpful."}, {"role": "user", "content": "Hi"}]
        await provider.chat(messages)

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["messages"] == messages

    @patch("infrastructure.llm.openai_provider.settings")
    @patch("infrastructure.llm.openai_provider.AsyncOpenAI")
    async def test_chat_empty_message_content(self, mock_openai_cls, mock_settings):
        _default_settings(mock_settings)
        usage = MagicMock(prompt_tokens=10, completion_tokens=0)
        choice = MagicMock()
        choice.message.content = None
        response = MagicMock()
        response.choices = [choice]
        response.usage = usage
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=response)
        mock_openai_cls.return_value = mock_client

        provider = OpenAIProvider()
        result = await provider.chat([{"role": "user", "content": "Hi"}])
        assert result.content == ""
        assert result.tokens_entrada == 10

    @patch("infrastructure.llm.openai_provider.settings")
    @patch("infrastructure.llm.openai_provider.AsyncOpenAI")
    async def test_chat_none_usage_zero_tokens(self, mock_openai_cls, mock_settings):
        _default_settings(mock_settings)
        choice = MagicMock()
        choice.message.content = "Hello"
        response = MagicMock()
        response.choices = [choice]
        response.usage = None
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=response)
        mock_openai_cls.return_value = mock_client

        provider = OpenAIProvider()
        result = await provider.chat([{"role": "user", "content": "Hi"}])
        assert result.tokens_entrada == 0
        assert result.tokens_salida == 0

    # chat_json ---------------------------------------------------------------

    @patch("infrastructure.llm.openai_provider.settings")
    @patch("infrastructure.llm.openai_provider.AsyncOpenAI")
    async def test_chat_json_returns_parsed_dict(self, mock_openai_cls, mock_settings):
        _default_settings(mock_settings)
        text = '{"explicacion": "done", "hallazgos_enriquecidos": [{"nit": "123"}]}'
        mock_response = _mock_openai_response(text)
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_cls.return_value = mock_client

        provider = OpenAIProvider()
        result = await provider.chat_json([{"role": "user", "content": "Go"}])
        assert result == {"explicacion": "done", "hallazgos_enriquecidos": [{"nit": "123"}], "tokens_entrada": 50, "tokens_salida": 30}

    @patch("infrastructure.llm.openai_provider.settings")
    @patch("infrastructure.llm.openai_provider.AsyncOpenAI")
    async def test_chat_json_invalid_json_fallback(self, mock_openai_cls, mock_settings):
        _default_settings(mock_settings)
        mock_response = _mock_openai_response("{bad}")
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_cls.return_value = mock_client

        provider = OpenAIProvider()
        result = await provider.chat_json([{"role": "user", "content": "X"}])
        assert result == {"explicacion": "{bad}", "hallazgos_enriquecidos": [], "tokens_entrada": 50, "tokens_salida": 30}

    @patch("infrastructure.llm.openai_provider.settings")
    @patch("infrastructure.llm.openai_provider.AsyncOpenAI")
    async def test_chat_json_no_json_fallback(self, mock_openai_cls, mock_settings):
        _default_settings(mock_settings)
        mock_response = _mock_openai_response("just text")
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_cls.return_value = mock_client

        provider = OpenAIProvider()
        result = await provider.chat_json([{"role": "user", "content": "X"}])
        assert result == {"explicacion": "just text", "hallazgos_enriquecidos": [], "tokens_entrada": 50, "tokens_salida": 30}

    @patch("infrastructure.llm.openai_provider.settings")
    @patch("infrastructure.llm.openai_provider.AsyncOpenAI")
    async def test_chat_json_null_content_fallback(self, mock_openai_cls, mock_settings):
        _default_settings(mock_settings)
        choice = MagicMock()
        choice.message.content = None
        response = MagicMock()
        response.choices = [choice]
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=response)
        mock_openai_cls.return_value = mock_client

        provider = OpenAIProvider()
        result = await provider.chat_json([{"role": "user", "content": "X"}])
        assert result == {"tokens_entrada": 0, "tokens_salida": 0}


# ═══════════════════════════════════════════════════════════════════════════════
# HuggingFaceProvider
# ═══════════════════════════════════════════════════════════════════════════════

class TestHuggingFaceProvider:

    @patch("infrastructure.llm.huggingface_provider.settings")
    @patch("infrastructure.llm.huggingface_provider.AsyncOpenAI")
    async def test_chat_returns_llm_response(self, mock_openai_cls, mock_settings):
        _default_settings(mock_settings)
        mock_response = _mock_openai_response("HF reply", 40, 15)
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_cls.return_value = mock_client

        provider = HuggingFaceProvider()
        result = await provider.chat([{"role": "user", "content": "Hi"}])

        assert result.content == "HF reply"
        assert result.tokens_entrada == 40
        assert result.tokens_salida == 15
        assert result.provider == "huggingface"

    @patch("infrastructure.llm.huggingface_provider.settings")
    @patch("infrastructure.llm.huggingface_provider.AsyncOpenAI")
    async def test_chat_uses_default_base_url_when_not_configured(self, mock_openai_cls, mock_settings):
        _default_settings(mock_settings)
        mock_settings.llm_tier3_api_base = ""
        mock_response = _mock_openai_response("OK")
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_cls.return_value = mock_client

        provider = HuggingFaceProvider()

        call_kwargs = mock_openai_cls.call_args.kwargs
        assert call_kwargs["base_url"] == "https://api-inference.huggingface.co/v1"

    @patch("infrastructure.llm.huggingface_provider.settings")
    @patch("infrastructure.llm.huggingface_provider.AsyncOpenAI")
    async def test_chat_uses_custom_base_url(self, mock_openai_cls, mock_settings):
        _default_settings(mock_settings)
        mock_settings.llm_tier3_api_base = "https://custom.hf.example.com/v1"
        mock_response = _mock_openai_response("OK")
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_cls.return_value = mock_client

        provider = HuggingFaceProvider()

        call_kwargs = mock_openai_cls.call_args.kwargs
        assert call_kwargs["base_url"] == "https://custom.hf.example.com/v1"

    @patch("infrastructure.llm.huggingface_provider.settings")
    @patch("infrastructure.llm.huggingface_provider.AsyncOpenAI")
    async def test_chat_json_returns_parsed_dict(self, mock_openai_cls, mock_settings):
        _default_settings(mock_settings)
        text = '{"explicacion": "ok", "hallazgos_enriquecidos": []}'
        mock_response = _mock_openai_response(text)
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_cls.return_value = mock_client

        provider = HuggingFaceProvider()
        result = await provider.chat_json([{"role": "user", "content": "X"}])
        assert result == {"explicacion": "ok", "hallazgos_enriquecidos": [], "tokens_entrada": 50, "tokens_salida": 30}

    @patch("infrastructure.llm.huggingface_provider.settings")
    @patch("infrastructure.llm.huggingface_provider.AsyncOpenAI")
    async def test_chat_json_invalid_fallback(self, mock_openai_cls, mock_settings):
        _default_settings(mock_settings)
        mock_response = _mock_openai_response("bad json")
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_cls.return_value = mock_client

        provider = HuggingFaceProvider()
        result = await provider.chat_json([{"role": "user", "content": "X"}])
        assert result == {"explicacion": "bad json", "hallazgos_enriquecidos": [], "tokens_entrada": 50, "tokens_salida": 30}

    @patch("infrastructure.llm.huggingface_provider.settings")
    @patch("infrastructure.llm.huggingface_provider.AsyncOpenAI")
    async def test_chat_json_empty_fallback(self, mock_openai_cls, mock_settings):
        _default_settings(mock_settings)
        choice = MagicMock()
        choice.message.content = None
        response = MagicMock()
        response.choices = [choice]
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=response)
        mock_openai_cls.return_value = mock_client

        provider = HuggingFaceProvider()
        result = await provider.chat_json([{"role": "user", "content": "X"}])
        assert result == {"tokens_entrada": 0, "tokens_salida": 0}


# ═══════════════════════════════════════════════════════════════════════════════
# NvidiaNIMProvider
# ═══════════════════════════════════════════════════════════════════════════════

class TestNvidiaNIMProvider:

    @patch("infrastructure.llm.nvidia_nim_provider.settings")
    @patch("infrastructure.llm.nvidia_nim_provider.AsyncOpenAI")
    async def test_chat_returns_llm_response(self, mock_openai_cls, mock_settings):
        _default_settings(mock_settings)
        mock_response = _mock_openai_response("NVIDIA reply", 70, 25)
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_cls.return_value = mock_client

        provider = NvidiaNIMProvider()
        result = await provider.chat([{"role": "user", "content": "Hi"}])

        assert result.content == "NVIDIA reply"
        assert result.tokens_entrada == 70
        assert result.tokens_salida == 25
        assert result.provider == "nvidia_nim"

    @patch("infrastructure.llm.nvidia_nim_provider.settings")
    @patch("infrastructure.llm.nvidia_nim_provider.AsyncOpenAI")
    async def test_chat_uses_default_base_url(self, mock_openai_cls, mock_settings):
        _default_settings(mock_settings)
        mock_settings.llm_tier2_api_base = ""
        mock_response = _mock_openai_response("OK")
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_cls.return_value = mock_client

        provider = NvidiaNIMProvider()

        call_kwargs = mock_openai_cls.call_args.kwargs
        assert call_kwargs["base_url"] == "https://integrate.api.nvidia.com/v1"

    @patch("infrastructure.llm.nvidia_nim_provider.settings")
    @patch("infrastructure.llm.nvidia_nim_provider.AsyncOpenAI")
    async def test_chat_uses_custom_base_url(self, mock_openai_cls, mock_settings):
        _default_settings(mock_settings)
        mock_settings.llm_tier2_api_base = "https://custom.nvidia.example.com/v1"
        mock_response = _mock_openai_response("OK")
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_cls.return_value = mock_client

        provider = NvidiaNIMProvider()

        call_kwargs = mock_openai_cls.call_args.kwargs
        assert call_kwargs["base_url"] == "https://custom.nvidia.example.com/v1"

    @patch("infrastructure.llm.nvidia_nim_provider.settings")
    @patch("infrastructure.llm.nvidia_nim_provider.AsyncOpenAI")
    async def test_chat_json_returns_parsed_dict(self, mock_openai_cls, mock_settings):
        _default_settings(mock_settings)
        text = '{"explicacion": "nvidia ok", "hallazgos_enriquecidos": []}'
        mock_response = _mock_openai_response(text)
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_cls.return_value = mock_client

        provider = NvidiaNIMProvider()
        result = await provider.chat_json([{"role": "user", "content": "X"}])
        assert result == {"explicacion": "nvidia ok", "hallazgos_enriquecidos": [], "tokens_entrada": 50, "tokens_salida": 30}

    @patch("infrastructure.llm.nvidia_nim_provider.settings")
    @patch("infrastructure.llm.nvidia_nim_provider.AsyncOpenAI")
    async def test_chat_json_invalid_fallback(self, mock_openai_cls, mock_settings):
        _default_settings(mock_settings)
        mock_response = _mock_openai_response("nope")
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_cls.return_value = mock_client

        provider = NvidiaNIMProvider()
        result = await provider.chat_json([{"role": "user", "content": "X"}])
        assert result == {"explicacion": "nope", "hallazgos_enriquecidos": [], "tokens_entrada": 50, "tokens_salida": 30}

    @patch("infrastructure.llm.nvidia_nim_provider.settings")
    @patch("infrastructure.llm.nvidia_nim_provider.AsyncOpenAI")
    async def test_chat_json_empty_fallback(self, mock_openai_cls, mock_settings):
        _default_settings(mock_settings)
        choice = MagicMock()
        choice.message.content = None
        response = MagicMock()
        response.choices = [choice]
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=response)
        mock_openai_cls.return_value = mock_client

        provider = NvidiaNIMProvider()
        result = await provider.chat_json([{"role": "user", "content": "X"}])
        assert result == {"tokens_entrada": 0, "tokens_salida": 0}


# ═══════════════════════════════════════════════════════════════════════════════
# Descubrimiento de Modelos
# ═══════════════════════════════════════════════════════════════════════════════

class TestNvidiaNIMProviderDiscovery:

    @patch("infrastructure.llm.nvidia_nim_provider.settings")
    @patch("infrastructure.llm.nvidia_nim_provider.AsyncOpenAI")
    async def test_discover_models_returns_list(self, mock_openai_cls, mock_settings):
        _default_settings(mock_settings)
        mock_models = MagicMock()
        mock_models.data = [
            MagicMock(id="meta/llama-3.1-8b-instruct"),
            MagicMock(id="mistralai/mistral-7b-instruct-v0.3"),
            MagicMock(id="qwen/qwen2.5-7b-instruct"),
        ]
        mock_client = MagicMock()
        mock_client.models.list = AsyncMock(return_value=mock_models)
        mock_openai_cls.return_value = mock_client

        provider = NvidiaNIMProvider()
        models = await provider.discover_models()

        assert isinstance(models, list)
        assert "meta/llama-3.1-8b-instruct" in models
        assert "mistralai/mistral-7b-instruct-v0.3" in models

    @patch("infrastructure.llm.nvidia_nim_provider.settings")
    @patch("infrastructure.llm.nvidia_nim_provider.AsyncOpenAI")
    async def test_discover_models_api_error_returns_empty(self, mock_openai_cls, mock_settings):
        _default_settings(mock_settings)
        mock_client = MagicMock()
        mock_client.models.list = AsyncMock(side_effect=Exception("API error"))
        mock_openai_cls.return_value = mock_client

        provider = NvidiaNIMProvider()
        models = await provider.discover_models()

        assert models == []


class TestHuggingFaceProviderDiscovery:

    @patch("infrastructure.llm.huggingface_provider.settings")
    @patch("infrastructure.llm.huggingface_provider.AsyncOpenAI")
    async def test_discover_models_returns_list(self, mock_openai_cls, mock_settings):
        _default_settings(mock_settings)
        mock_models = MagicMock()
        mock_models.data = [
            MagicMock(id="Qwen/Qwen2.5-7B-Instruct"),
            MagicMock(id="mistralai/Mistral-7B-Instruct-v0.3"),
        ]
        mock_client = MagicMock()
        mock_client.models.list = AsyncMock(return_value=mock_models)
        mock_openai_cls.return_value = mock_client

        provider = HuggingFaceProvider()
        models = await provider.discover_models()

        assert isinstance(models, list)
        assert "Qwen/Qwen2.5-7B-Instruct" in models

    @patch("infrastructure.llm.huggingface_provider.settings")
    @patch("infrastructure.llm.huggingface_provider.AsyncOpenAI")
    async def test_discover_models_api_error_returns_empty(self, mock_openai_cls, mock_settings):
        _default_settings(mock_settings)
        mock_client = MagicMock()
        mock_client.models.list = AsyncMock(side_effect=Exception("Connection error"))
        mock_openai_cls.return_value = mock_client

        provider = HuggingFaceProvider()
        models = await provider.discover_models()

        assert models == []


class TestOpenAIProviderDiscovery:

    @patch("infrastructure.llm.openai_provider.settings")
    @patch("infrastructure.llm.openai_provider.AsyncOpenAI")
    async def test_discover_models_returns_list(self, mock_openai_cls, mock_settings):
        _default_settings(mock_settings)
        mock_models = MagicMock()
        mock_models.data = [
            MagicMock(id="gpt-4o"),
            MagicMock(id="gpt-4o-mini"),
            MagicMock(id="gpt-3.5-turbo"),
        ]
        mock_client = MagicMock()
        mock_client.models.list = AsyncMock(return_value=mock_models)
        mock_openai_cls.return_value = mock_client

        provider = OpenAIProvider()
        models = await provider.discover_models()

        assert isinstance(models, list)
        assert "gpt-4o" in models

    @patch("infrastructure.llm.openai_provider.settings")
    @patch("infrastructure.llm.openai_provider.AsyncOpenAI")
    async def test_discover_models_api_error_returns_empty(self, mock_openai_cls, mock_settings):
        _default_settings(mock_settings)
        mock_client = MagicMock()
        mock_client.models.list = AsyncMock(side_effect=Exception("Rate limit"))
        mock_openai_cls.return_value = mock_client

        provider = OpenAIProvider()
        models = await provider.discover_models()

        assert models == []


class TestAnthropicProviderDiscovery:

    @patch("infrastructure.llm.anthropic_provider.settings")
    @patch("infrastructure.llm.anthropic_provider.anthropic.AsyncAnthropic")
    async def test_discover_models_returns_known_models(self, mock_anthropic_cls, mock_settings):
        _default_settings(mock_settings)
        mock_anthropic_cls.return_value = MagicMock()

        provider = AnthropicProvider()
        models = await provider.discover_models()

        assert isinstance(models, list)
        assert len(models) > 0
        assert "claude-sonnet-4-20250506" in models
