"""Application settings, loaded from environment variables (and `.env` in local dev).

Secrets are typed as `SecretStr` so they never leak into logs or reprs.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

type Environment = Literal["dev", "test", "prod"]
type LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: Environment = "dev"
    log_level: LogLevel = "INFO"

    # Vector store
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: SecretStr | None = None
    qdrant_collection: str = "chunks"

    # LLM
    llm_api_key: SecretStr | None = None
    llm_model: str = "llama-3.3-70b-versatile"
    llm_timeout_s: float = Field(default=30.0, gt=0)
    llm_max_retries: int = Field(default=3, ge=0)

    # Embeddings
    embedding_model: str = "BAAI/bge-small-en-v1.5"


@lru_cache
def get_settings() -> Settings:
    return Settings()
