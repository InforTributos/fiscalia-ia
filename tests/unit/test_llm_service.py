from unittest.mock import AsyncMock, patch

from infrastructure.llm.llm_service import LLMService


@patch("infrastructure.llm.llm_service.settings")
def test_llm_service_sin_providers(mock_settings):
    mock_settings.llm_tier1_api_key = ""
    mock_settings.llm_tier1_provider = ""
    mock_settings.llm_tier2_api_key = ""
    mock_settings.llm_tier3_api_key = ""
    service = LLMService()
    assert len(service.providers) == 0
    assert service.providers_count == 0
    assert service.provider_names == []


async def test_analyze_degradado_retorna_respuesta():
    service = LLMService()
    result = await service.analyze([{"role": "user", "content": "test"}])
    assert isinstance(result["explicacion"], str)
    assert len(result["explicacion"]) > 10


async def test_analyze_con_provider_exitoso():
    service = LLMService()
    mock_provider = AsyncMock()
    mock_provider.chat_json = AsyncMock(return_value={
        "explicacion": "test response",
        "tokens_entrada": 10,
        "tokens_salida": 5,
    })
    mock_provider.name = "test_provider"
    service.providers = [mock_provider]

    result = await service.analyze([{"role": "user", "content": "test"}])
    assert result["explicacion"] == "test response"
    mock_provider.chat_json.assert_awaited_once()


async def test_analyze_todos_fallan_retorna_degradado():
    service = LLMService()
    mock_provider = AsyncMock()
    mock_provider.chat_json = AsyncMock(side_effect=Exception("API error"))
    mock_provider.name = "failing_provider"
    service.providers = [mock_provider]

    result = await service.analyze([{"role": "user", "content": "test"}])
    assert result["modo_degradado"] is True
    assert "API error" in result.get("error", "")


class TestAsyncInit:

    @patch("infrastructure.llm.llm_service.settings")
    async def test_async_init_discover_models_when_no_model(self, mock_settings):
        mock_settings.llm_tier1_api_key = "sk-test"
        mock_settings.llm_tier1_provider = "anthropic"
        mock_settings.llm_tier1_model = ""
        mock_settings.llm_tier2_api_key = ""
        mock_settings.llm_tier3_api_key = ""
        mock_settings.llm_rate_limit_rpm = 40

        service = LLMService()
        mock_provider = AsyncMock()
        mock_provider.discover_models = AsyncMock(return_value=["claude-sonnet-4-20250506", "claude-3-haiku-20240307"])
        mock_provider.model = ""
        service.providers = [mock_provider]

        await service.async_init()

        mock_provider.discover_models.assert_awaited_once()
        assert mock_provider.model in ["claude-sonnet-4-20250506", "claude-3-haiku-20240307"]

    @patch("infrastructure.llm.llm_service.settings")
    async def test_async_init_skips_discovery_when_model_already_set(self, mock_settings):
        mock_settings.llm_tier1_api_key = "sk-test"
        mock_settings.llm_tier1_provider = "anthropic"
        mock_settings.llm_tier1_model = "claude-3-sonnet-20241022"
        mock_settings.llm_tier2_api_key = ""
        mock_settings.llm_tier3_api_key = ""
        mock_settings.llm_rate_limit_rpm = 40

        service = LLMService()
        mock_provider = AsyncMock()
        mock_provider.model = "claude-3-sonnet-20241022"
        mock_provider.discover_models = AsyncMock(return_value=["gpt-4o"])
        service.providers = [mock_provider]

        await service.async_init()

        # No debe llamar a discover_models si ya tiene modelo configurado
        mock_provider.discover_models.assert_not_called()
        assert mock_provider.model == "claude-3-sonnet-20241022"

    @patch("infrastructure.llm.llm_service.settings")
    async def test_async_init_discovery_preserves_existing_model(self, mock_settings):
        mock_settings.llm_tier1_api_key = "sk-test"
        mock_settings.llm_tier1_provider = "anthropic"
        mock_settings.llm_tier1_model = ""
        mock_settings.llm_tier2_api_key = ""
        mock_settings.llm_tier3_api_key = ""
        mock_settings.llm_rate_limit_rpm = 40

        service = LLMService()
        mock_provider = AsyncMock()
        mock_provider.model = "claude-3-haiku-20240307"
        service.providers = [mock_provider]

        await service.async_init()

        assert mock_provider.model == "claude-3-haiku-20240307"
