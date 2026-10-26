# Investigation Engine

Multi-hop, evidence-grounded question answering over large document collections:
hybrid retrieval, agentic RAG with citations, abstention, and contradiction detection.

**Live demo:** https://investigation-engine-xi.vercel.app — the web app currently runs against
a mocked API; the backend is being connected.

> Work in progress. Architecture, evaluation and deployment docs will be added as the system lands.

## Repository layout

| Path | Contents |
|---|---|
| `apps/api` | Python backend (FastAPI), managed with uv |
| `apps/web` | Web UI (React, TypeScript, Vite, Tailwind CSS), managed with pnpm |
| `docs/` | Project documentation, including the AI usage log |
| `AGENTS.md`, `CLAUDE.md`, `.claude/` | Instructions and tooling for AI coding agents (see below) |

## Local development

Requires [uv](https://docs.astral.sh/uv/) (it installs the pinned Python version itself),
Node.js 22+, pnpm and Docker.

```bash
make services-up    # local Postgres and Qdrant

cp apps/api/.env.example apps/api/.env
make api-install
make api-dev        # http://localhost:8000/health

cp apps/web/.env.example apps/web/.env.local
make web-install
make web-dev        # http://localhost:5173
```

`VITE_API_MOCKING` decides which API calls the web app answers in the browser with mock data
([Mock Service Worker](https://mswjs.io)): `enabled` (all — no backend needed),
`investigations` (only investigations; documents use the real API at `VITE_API_BASE_URL`) or
`disabled` (none).

## Data

Two corpora, both loaded as read-only `dataset` documents into the services in
`apps/api/.env`. Both loaders are idempotent: a rerun skips what is already stored.

```bash
make data-hotpotqa    # 66,581 HotpotQA paragraphs (~45 min on a laptop CPU)
make data-synthetic   # 11 Northwind Pay documents in PDF, DOCX, Markdown and TXT
```

- **HotpotQA** — every distinct paragraph of the
  [dev distractor set](https://huggingface.co/datasets/hotpotqa/hotpot_qa), pinned to a
  dataset revision and SHA-256. Its 7,405 questions come with their supporting paragraphs,
  which are inside the corpus, so the same file gives the evaluation its gold answers.
- **Northwind Pay** — a small synthetic company corpus with planted facts, multi-hop chains,
  contradictions and unanswerable questions, documented in
  [`docs/evaluation/northwind-ground-truth.md`](docs/evaluation/northwind-ground-truth.md).

## Deployment

| Part | Where | How |
|---|---|---|
| Web | Vercel | Builds `apps/web` on every push. `VITE_API_BASE_URL` and `VITE_API_MOCKING` are set in the Vercel project; a production build without either fails on purpose. |
| API | AWS EC2 (t3.small), Stockholm | `.github/workflows/deploy-api.yml` builds `apps/api/Dockerfile`, pushes it to GitHub Container Registry and restarts `apps/api/deploy/compose.yaml` on the host over SSH, after the API checks pass on `main`. Caddy in front of the API serves HTTPS with a Let's Encrypt certificate for `<ip-with-dashes>.sslip.io`. |
| Data | Neon (Postgres), Qdrant Cloud, both Frankfurt | Loaded with the `make data-*` targets above, pointed at the cloud services. |

Secrets: the API's settings (`DATABASE_URL`, `QDRANT_URL`, `QDRANT_API_KEY`, `LLM_API_KEY`,
`CORS_ORIGINS`) live only in `/opt/investigation-engine/.env` on the host (mode 600); GitHub
holds only the host address and its SSH key. One-time host setup:
`apps/api/deploy/bootstrap.sh`.

## Quality gates

```bash
make api-format     # auto-format and auto-fix
make api-check      # lint, format check, mypy, tests (same as CI)

make web-format
make web-check      # lint, format check, type check, tests, build (same as CI)
```

Run `make help` for all targets.

## Working with AI agents

The repository is set up for AI coding agents, and every AI-assisted change is logged in
[`docs/ai-usage.md`](docs/ai-usage.md).

- **`AGENTS.md`** (root, `apps/api`, `apps/web`) — scope, commands, conventions and the
  API contract, in the cross-tool `AGENTS.md` format. `CLAUDE.md` files import them for
  Claude Code.
- **`.claude/settings.json`** — the agent may run the quality gates; it may not read `.env`
  files or commit/push.
- **`.claude/hooks/format-edited-file.mjs`** — formats every file the agent edits with ruff
  or Prettier.
- **`.claude/agents/`** — read-only reviewers: `contract-guardian` (backend ↔ frontend ↔
  mocks) and `convention-reviewer` (repo conventions and scope).
- **`.claude/skills/`** — `/check`, `/add-endpoint`, `/log-ai-usage`.
