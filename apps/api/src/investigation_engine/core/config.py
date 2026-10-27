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

    # LLM: any OpenAI-compatible chat completions API; Groq by default. The fallback model
    # answers when the main one keeps failing (e.g. its daily token quota is used up).
    llm_api_key: SecretStr | None = None
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_model: str = "openai/gpt-oss-120b"
    llm_fallback_model: str | None = "openai/gpt-oss-20b"
    llm_timeout_s: float = Field(default=60.0, gt=0)
    llm_max_retries: int = Field(default=3, ge=0)

    # Evaluation judge: a model from another family than the agent's, possibly on another
    # provider. The key falls back to LLM_API_KEY when both use the same provider.
    judge_base_url: str = "https://api.groq.com/openai/v1"
    judge_model: str = "qwen/qwen3.8-27b"
    judge_api_key: SecretStr | None = None

    # Investigation agent: the most LLM turns (search or answer) before it must answer, and
    # how many passages one search returns. Both bound the tokens a question costs.
    agent_max_turns: int = Field(default=4, gt=0)
    agent_search_limit: int = Field(default=6, gt=0)
    # One more search and LLM call per answer, to catch sources that disagree with it.
    agent_cross_check: bool = False

    # Daily investigation caps (UTC days), per client IP and in total: the free LLM tier
    # allows roughly 50 investigations a day, and the demo must not run dry.
    investigations_per_client_per_day: int = Field(default=20, gt=0)
    investigations_per_day: int = Field(default=40, gt=0)

    # Answer cache: recent answers by question; any document change clears it, and the time
    # limit bounds changes made outside the API (the dataset scripts). 0 entries turns it off.
    answer_cache_size: int = Field(default=500, ge=0)
    answer_cache_ttl_s: float = Field(default=24 * 3600, gt=0)

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
    # Re-ranking: a cross-encoder reorders the top fused candidates; None turns it off.
    # Off by default: MiniLM-L-6 raised retrieval MRR from 0.880 to 0.932, but answers were
    # not better with it (docs/decisions/0011-cross-encoder-reranking.md). To try it:
    # RERANK_MODEL=Xenova/ms-marco-MiniLM-L-6-v2.
    rerank_model: str | None = None
    rerank_candidates: int = Field(default=20, gt=0)

    # Chunking (sizes in words; overlap applies to the fixed strategy only)
    chunking_strategy: ChunkingStrategy = "structured"
    chunk_max_words: int = Field(default=200, gt=0)
    chunk_overlap_words: int = Field(default=40, ge=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
