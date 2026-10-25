# Investigation Engine

Multi-hop, evidence-grounded question answering over large document collections:
hybrid retrieval, agentic RAG with citations, abstention, and contradiction detection.

> Work in progress. Architecture, evaluation and deployment docs will be added as the system lands.

## Repository layout

| Path | Contents |
|---|---|
| `apps/api` | Python backend (FastAPI), managed with uv |
| `apps/web` | Web UI (React, TypeScript, Vite, Tailwind CSS), managed with pnpm |

## Local development

Requires [uv](https://docs.astral.sh/uv/) (it installs the pinned Python version itself),
Node.js 22+ and pnpm.

```bash
cp apps/api/.env.example apps/api/.env
make api-install
make api-dev        # http://localhost:8000/health

cp apps/web/.env.example apps/web/.env.local
make web-install
make web-dev        # http://localhost:5173
```

With `VITE_API_MOCKING=enabled` the web app answers API calls in the browser with mock data
([Mock Service Worker](https://mswjs.io)), so it runs without the backend. Set it to `disabled`
to use the real API at `VITE_API_BASE_URL`.

## Quality gates

```bash
make api-format     # auto-format and auto-fix
make api-check      # lint, format check, mypy, tests (same as CI)

make web-format
make web-check      # lint, format check, type check, tests, build (same as CI)
```

Run `make help` for all targets.
