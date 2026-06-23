from unittest.mock import AsyncMock

from infrastructure.llm.llm_service import LLMService


def test_llm_service_sin_providers():
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
