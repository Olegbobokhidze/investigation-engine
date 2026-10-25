# Investigation Engine

Multi-hop, evidence-grounded question answering over large document collections:
hybrid retrieval, agentic RAG with citations, abstention, and contradiction detection.

> Work in progress. Architecture, evaluation and deployment docs will be added as the system lands.

## Repository layout

| Path | Contents |
|---|---|
| `apps/api` | Python backend (FastAPI), managed with uv |

## Local development

```bash
cd apps/api
uv sync
cp .env.example .env
uv run uvicorn --factory investigation_engine.main:create_app --reload
```

## Quality gates

```bash
cd apps/api
uv run ruff check . && uv run ruff format --check .
uv run mypy src tests
uv run pytest
```
