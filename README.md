# Investigation Engine

Multi-hop, evidence-grounded question answering over large document collections:
hybrid retrieval, agentic RAG with citations, abstention, and contradiction detection.

> Work in progress. Architecture, evaluation and deployment docs will be added as the system lands.

## Repository layout

| Path | Contents |
|---|---|
| `apps/api` | Python backend (FastAPI), managed with uv |

## Local development

Requires [uv](https://docs.astral.sh/uv/); it installs the pinned Python version itself.

```bash
cp apps/api/.env.example apps/api/.env
make api-install
make api-dev        # http://localhost:8000/health
```

## Quality gates

```bash
make api-format     # auto-format and auto-fix
make api-check      # lint, format check, mypy, tests (same as CI)
```

Run `make help` for all targets.
