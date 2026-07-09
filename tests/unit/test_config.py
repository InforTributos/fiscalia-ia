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


def test_settings_oracle_vars_defaults():
    overrides = {
        "LLM_TIER1_API_KEY": "",
        "LLM_TIER2_API_KEY": "",
        "LLM_TIER3_API_KEY": "",
        "POSTGRES_PASSWORD": "",
        "ORACLE_HOST": "localhost",
        "ORACLE_SERVICE": "",
        "ORACLE_USER": "",
        "ORACLE_PASSWORD": "",
    }
    with _overrides(**overrides):
        from config import Settings
        s = Settings()
        assert s.oracle_host == "localhost"
        assert s.oracle_port == 1521
        assert s.oracle_service == ""
        assert s.oracle_user == ""
        assert s.oracle_password == ""
        assert s.oracle_pool_min == 2


def test_settings_oracle_vars_from_env():
    overrides = {
        "LLM_TIER1_API_KEY": "",
        "LLM_TIER2_API_KEY": "",
        "LLM_TIER3_API_KEY": "",
        "POSTGRES_PASSWORD": "",
        "ORACLE_USER": "fiscalia_app",
        "ORACLE_PASSWORD": "secret",
        "ORACLE_HOST": "10.0.0.1",
        "ORACLE_PORT": "1525",
        "ORACLE_SERVICE": "MYSVC",
        "ORACLE_POOL_MIN": "5",
    }
    with _overrides(**overrides):
        from config import Settings
        s = Settings()
        assert s.oracle_host == "10.0.0.1"
        assert s.oracle_port == 1525
        assert s.oracle_service == "MYSVC"
        assert s.oracle_pool_min == 5


def test_settings_oracle_rechaza_changeme_user():
    overrides = {
        "LLM_TIER1_API_KEY": "",
        "LLM_TIER2_API_KEY": "",
        "LLM_TIER3_API_KEY": "",
        "POSTGRES_PASSWORD": "",
        "ORACLE_USER": "changeme",
        "ORACLE_PASSWORD": "secret",
    }
    with _overrides(**overrides):
        from config import Settings
        with pytest.raises(ValidationError):
            Settings()


def test_settings_oracle_rechaza_changeme_password():
    overrides = {
        "LLM_TIER1_API_KEY": "",
        "LLM_TIER2_API_KEY": "",
        "LLM_TIER3_API_KEY": "",
        "POSTGRES_PASSWORD": "",
        "ORACLE_USER": "fiscalia_app",
        "ORACLE_PASSWORD": "changeme",
    }
    with _overrides(**overrides):
        from config import Settings
        with pytest.raises(ValidationError):
            Settings()


def test_setup_logging_retorna_logger():
    from config import setup_logging
    logger = setup_logging()
    assert logger.name == "fiscalia"
