import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError


def _overrides(**kwargs):
    """Return env overrides that take precedence over .env file."""
    base = {
        "POSTGRES_PASSWORD": "",
        "LLM_TIER1_API_KEY": "",
        "LLM_TIER2_API_KEY": "",
        "LLM_TIER3_API_KEY": "",
    }
    base.update(kwargs)
    return patch.dict(os.environ, base, clear=False)


def test_settings_carga_con_defaults():
    with _overrides():
        from config import Settings
        s = Settings()
        assert s.api_port == 8000
        assert s.log_level == "INFO"
        assert s.postgres_password == ""


def test_settings_lee_variables():
    overrides = {
        "API_PORT": "9000",
        "POSTGRES_HOST": "10.0.0.1",
        "LLM_TIER1_API_KEY": "sk-real-key",
    }
    with _overrides(**overrides):
        from config import Settings
        s = Settings()
        assert s.api_port == 9000
        assert s.postgres_host == "10.0.0.1"
        assert s.llm_tier1_api_key == "sk-real-key"


def test_settings_rechaza_placeholder_api_key():
    with _overrides(LLM_TIER1_API_KEY="changeme"):
        from config import Settings
        with pytest.raises(ValidationError):
            Settings()


def test_settings_rechaza_placeholder_password():
    with _overrides(POSTGRES_PASSWORD="changeme"):
        from config import Settings
        with pytest.raises(ValidationError):
            Settings()


def test_setup_logging_retorna_logger():
    from config import setup_logging
    logger = setup_logging()
    assert logger.name == "fiscalia"
