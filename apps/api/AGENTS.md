# Backend (apps/api) — agent guide

Python 3.12, FastAPI, Pydantic v2, uv. Run commands from the repo root via `make api-*`, or
from this folder via `uv run …`.

## Layout

```
src/investigation_engine/
├── core/        config, logging, errors — no imports from other packages here
├── api/         HTTP only: routes/, schemas, dependencies; no business logic
├── documents/   document CRUD, dedup, origin rules
├── ingestion/   loaders (pdf, docx, md, txt), chunking strategies, pipeline
├── retrieval/   embeddings, vector store, keyword search, fusion, reranking
├── llm/         LLM client (timeouts, retries), prompts
├── investigation/  agentic RAG: planner, tools, verification, contradiction checks
├── datasets/    corpus loaders (HotpotQA, synthetic Northwind Pay) and bulk indexing
└── evaluation/  metrics and evaluation runners
tests/           mirrors src/ (tests/ingestion/test_loaders.py ↔ ingestion/loaders.py);
                 binary samples in tests/fixtures/
```

Dependencies point inward: `api` → services → adapters (Qdrant, Postgres, LLM). Services never
import FastAPI.

## Rules

- **Errors:** raise a subclass of `core.errors.AppError`; never `HTTPException` in services.
  `main.py` maps them to the error envelope. Add a new subclass with its own `code` rather
  than reusing a generic one.
- **Settings:** read through `core.config.get_settings()`. Secrets are `SecretStr`; call
  `.get_secret_value()` only at the point of use.
- **Logging:** `structlog.get_logger()`, event names in `snake_case`, context as keyword
  arguments: `log.info("document_indexed", document_id=..., chunk_count=...)`. Never log
  secrets or full document text.
- **Types:** `mypy --strict` must pass. No `Any` without a comment saying why.
- **API schemas:** Pydantic models extend the shared camelCase base model; field names stay
  snake_case in Python.
- **External calls** (LLM, Qdrant, embeddings) go through one adapter each, with timeouts,
  bounded retries and an `UpstreamError` on final failure.
- **Tests:** pytest, one behavior per test, Arrange / Act / Assert separated by blank lines,
  named `test_<unit>_<behavior>`. Fake external services; never call a paid API in tests.
- **Async:** route handlers are `async def`; never block the event loop with CPU-heavy or
  synchronous I/O work — offload it.
