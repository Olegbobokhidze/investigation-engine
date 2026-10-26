"""Application settings, loaded from environment variables (and `.env` in local dev).

Secrets are typed as `SecretStr` so they never leak into logs or reprs.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

type Environment = Literal["dev", "test", "prod"]
type LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]
type ChunkingStrategy = Literal["fixed", "structured"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: Environment = "dev"
    log_level: LogLevel = "INFO"

    # HTTP. Browser origins allowed to call the API; set as a JSON list in the environment.
    cors_origins: list[str] = ["http://localhost:5173"]
    max_upload_bytes: int = Field(default=10_000_000, gt=0)

    # Postgres: document records. A secret because the URL embeds the password.
    database_url: SecretStr = SecretStr(
        "postgresql://postgres:postgres@localhost:5440/investigation_engine"
    )

    # Vector store
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: SecretStr | None = None
    qdrant_collection: str = "chunks"

    # LLM
    llm_api_key: SecretStr | None = None
    llm_model: str = "llama-3.3-70b-versatile"
    llm_timeout_s: float = Field(default=30.0, gt=0)
    llm_max_retries: int = Field(default=3, ge=0)

    # Embeddings. BGE models are trained with this instruction in front of search queries
    # (not passages); fastembed doesn't add it, so we do.
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_query_prefix: str = "Represent this sentence for searching relevant passages: "

    # Hybrid search: candidates per retriever, then weighted RRF (see retrieval/fusion.py).
    # k=10 with equal weights beat the paper's k=60 and a down-weighted BM25 on every metric
    # in the retrieval evaluation (docs/evaluation/retrieval-hotpotqa.md).
    search_candidates: int = Field(default=40, gt=0)
    rrf_k: int = Field(default=10, ge=0)
    rrf_dense_weight: float = Field(default=1.0, ge=0)
    rrf_sparse_weight: float = Field(default=1.0, ge=0)

    # Chunking (sizes in words; overlap applies to the fixed strategy only)
    chunking_strategy: ChunkingStrategy = "structured"
    chunk_max_words: int = Field(default=200, gt=0)
    chunk_overlap_words: int = Field(default=40, ge=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
