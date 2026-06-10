import pytest
from unittest.mock import patch
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_verify_api_key_valida():
    from api.middleware.auth import verify_api_key
    with patch("api.middleware.auth.settings") as mock_settings:
        mock_settings.api_key = "secret-key"
        result = await verify_api_key("secret-key")
        assert result == "secret-key"


@pytest.mark.asyncio
async def test_verify_api_key_invalida():
    from api.middleware.auth import verify_api_key
    with patch("api.middleware.auth.settings") as mock_settings:
        mock_settings.api_key = "secret-key"
        with pytest.raises(HTTPException) as exc:
            await verify_api_key("wrong-key")
        assert exc.value.status_code == 401
        assert "inválida" in exc.value.detail
