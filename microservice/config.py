import logging
import time

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    api_port: int = 8000
    api_host: str = "0.0.0.0"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "fiscalia"
    postgres_user: str = "fiscalia"
    postgres_password: str = ""

    llm_tier1_api_key: str = ""
    llm_tier1_provider: str = "anthropic"
    llm_tier1_model: str = "claude-sonnet-4-20250506"
    llm_tier1_api_base: str | None = None

    llm_tier2_api_key: str = ""
    llm_tier2_model: str = "qwen/qwen2.5-7b-instruct"
    llm_tier2_api_base: str = "https://integrate.api.nvidia.com/v1"

    llm_tier3_api_key: str = ""
    llm_tier3_model: str = "Qwen/Qwen2.5-7B-Instruct"
    llm_tier3_api_base: str = "https://api-inference.huggingface.co/v1"

    llm_max_tokens: int = 4096
    llm_timeout: int = 60

    cache_ttl_seconds: int = 3600

    retry_max_attempts: int = 3
    retry_backoff_factor: int = 2
    retry_timeout: int = 60

    max_concurrent_processes: int = 5
    process_timeout_minutes: int = 30

    pool_min_size: int = 4
    pool_max_size: int = 20
    pool_timeout: int = 5

    log_level: str = "INFO"

    oracle_host: str = "localhost"
    oracle_port: int = 1521
    oracle_service: str = ""
    oracle_user: str = ""
    oracle_password: str = ""
    oracle_pool_min: int = 2
    oracle_pool_max: int = 5
    oracle_pool_timeout: int = 30

    startup_time: float = time.time()

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @field_validator("llm_tier1_api_key", "llm_tier2_api_key", "llm_tier3_api_key")
    @classmethod
    def _validar_placeholder(cls, v: str) -> str:
        if v and v.lower().startswith("changeme"):
            raise ValueError("API key tiene valor placeholder 'changeme' — debe configurarse con una clave real")
        return v

    @field_validator("postgres_password")
    @classmethod
    def _validar_db_password(cls, v: str) -> str:
        if v and v.lower().startswith("changeme"):
            raise ValueError("POSTGRES_PASSWORD tiene valor placeholder 'changeme'")
        return v

    @field_validator("oracle_user", "oracle_password")
    @classmethod
    def _validar_oracle_creds(cls, v: str) -> str:
        if v and v.lower().startswith("changeme"):
            raise ValueError("Oracle credential tiene valor placeholder 'changeme'")
        return v


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
