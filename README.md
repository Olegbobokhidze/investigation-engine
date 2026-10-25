# Investigation Engine

Multi-hop, evidence-grounded question answering over large document collections:
hybrid retrieval, agentic RAG with citations, abstention, and contradiction detection.

> Work in progress. Architecture, evaluation and deployment docs will be added as the system lands.

## Local development

```bash
uv sync
cp .env.example .env
uv run uvicorn app.main:app --reload
```

## Quality gates

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy app
uv run pytest
```
