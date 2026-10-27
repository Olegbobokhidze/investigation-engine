# Investigation Engine

Multi-hop, evidence-grounded question answering over large document collections:
hybrid retrieval, agentic RAG with citations, abstention, and contradiction detection.

**Live demo:** https://investigation-engine-xi.vercel.app (API:
https://13-53-155-129.sslip.io/health). Ask about the Northwind Pay incident ("Who was the
primary on-call engineer when INC-0412 started?", "When was CHG-2291 deployed?") or any of
the 66,581 HotpotQA Wikipedia paragraphs.

**Evaluation:** [`docs/evaluation-report.md`](docs/evaluation-report.md).

## How it works

```
question
  │
  ├─ 1. plan        the LLM splits it into 1–4 sub-questions          (decomposition)
  ├─ 2. search      hybrid search per sub-question: dense (bge-small) + BM25 in Qdrant,
  │                 fused with our weighted Reciprocal Rank Fusion      (retrieval/fusion.py)
  ├─ 3. investigate tool-calling loop, at most 4 turns: the LLM reads numbered passages and
  │                 calls search_documents (often with a name it just learned: the second
  │                 hop), get_document, or submit_answer                (investigation/agent.py)
  └─ 4. verify      citations must point at passages the LLM was shown; an answer with none
                    becomes an abstention; a conflict must cite both sides
                                                                        (investigation/citations.py)
```

- **Grounded:** every sentence cites passages as `[n]`; the UI links each to its source.
- **Abstains** (`insufficient_evidence`) when the documents don't answer the question.
- **Flags contradictions:** when sources disagree, the answer gives both values and each
  conflict names who says what.
- **LLM errors:** timeouts, retries with capped exponential backoff and `Retry-After`, a
  fallback model when the main one keeps failing, then a 502 with a readable message
  (`llm/client.py`). The client speaks the OpenAI-compatible API (Groq by default).

**Ingestion:** PDF, DOCX, Markdown and TXT uploads are parsed, normalized, deduplicated by
content hash (409 on a duplicate), split by structure-aware chunking and indexed in Postgres
(source of truth) and Qdrant (search index). Documents can be added, replaced and deleted;
the HotpotQA and Northwind datasets are read-only (403).

**Architecture:** a modular monolith in layers, HTTP (`api/`) → services → adapters
(Qdrant, Postgres, LLM). Services depend on protocols (`ChatModel`, `TextEmbedder`,
`Corpus`, `Chunker`), so the LLM, embedder or vector store is swapped, or faked in tests, in
one place.

| Endpoint | |
|---|---|
| `POST /investigations` | `{question}` → answer, cited sources, conflicts, steps |
| `GET /documents?search=&page=&pageSize=` | paginated document list |
| `POST /documents` | multipart `files`: one result per file (indexed, duplicate or failed) |
| `PUT /documents/{id}` | multipart `file`: replace an uploaded document |
| `DELETE /documents/{id}` | delete an uploaded document and its chunks |

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

## Evaluation

```bash
make eval-retrieval   # search configurations on 200 HotpotQA questions
make eval-chunking    # chunking strategies on Northwind (local Qdrant)
make eval-answers     # agent vs single-shot on 45 questions (uses LLM quota; resumable)
make eval-report      # metrics from the recorded answers, no LLM calls
```

Results and failure analysis: [`docs/evaluation-report.md`](docs/evaluation-report.md).

## Known limitations

- **Free-tier LLM.** Groq's free tier allows 8,000 tokens per minute and a daily token
  quota; an investigation uses about 4,000 tokens, so bursts of questions wait for the limit
  and a long evaluation run spans more than one day.
- **PDF paragraphs.** pypdf doesn't preserve paragraph breaks inside a page, so a PDF page's
  text is chunked by sentences rather than by paragraph.
- **No authentication.** Anyone with the URL can upload and delete *uploaded* documents
  (datasets are read-only). Fine for a demo, not for production.
- **Single region, single instance.** One EC2 host in Stockholm talks to Neon and Qdrant in
  Frankfurt; there is no replica.

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
