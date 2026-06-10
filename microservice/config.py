import logging
import time

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    api_port: int = 8000
    api_host: str = "0.0.0.0"
    api_key: str = "abc123..."

    oracle_dsn: str = "host:1521/service"
    oracle_user: str = "user"
    oracle_password: str = "pass"

    llm_mode: str = "primary_fallback"
    llm_primary_provider: str = "nvidia_nim"
    llm_primary_model: str = "meta/llama-3.3-70b-instruct"
    llm_primary_api_key: str = "nvapi-..."
    llm_primary_api_base: str | None = "https://integrate.api.nvidia.com/v1"

    llm_fallback_provider: str | None = "nvidia_nim"
    llm_fallback_model: str | None = "meta/llama-3.2-3b-instruct"
    llm_fallback_api_key: str | None = "nvapi-..."
    llm_fallback_api_base: str | None = "https://integrate.api.nvidia.com/v1"

    llm_max_tokens: int = 4096
    llm_timeout: int = 60

    cache_ttl_seconds: int = 3600

    retry_max_attempts: int = 3
    retry_backoff_factor: int = 2
    retry_timeout: int = 60

    log_level: str = "INFO"

    startup_time: float = time.time()

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()


def setup_logging():
    class JsonFormatter(logging.Formatter):
        def format(self, record):
            if isinstance(record.msg, dict):
                import json

                return json.dumps(record.msg, ensure_ascii=False)
            return super().format(record)

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger("fiscalia")
    root.addHandler(handler)
    root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    return root
