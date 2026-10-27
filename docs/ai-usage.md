# AI usage log

A running record of how AI tools were used on this project, kept as the work happens. The
final AI Usage Report is written from these entries. Newest first.

**Tools:** Claude Code (Claude Opus 5.5) in VS Code — code generation, review, UI design on a
canvas, and explanations. Repository setup for agents: `AGENTS.md`, `CLAUDE.md` and
`.claude/` (permissions, a format-on-edit hook, review subagents, workflow skills).

Each entry: **Task** · **AI contribution** · **Author decisions** · **Verification**.

---

## 2026-10-27

### Load test and this log

- **Task:** close the gaps found by comparing with another submission: no load test, and
  this log had stopped on 25 October.
- **AI contribution:** a load test of the live API's read endpoints at 1, 10 and 25 clients
  (`evaluation/load.py`, `make load-test`) with nearest-rank percentiles, p95 latency in the
  answer evaluation, and the findings in `docs/evaluation/load-test.md`; drafted the entries
  for 26 and 27 October from the session history.
- **Author decisions:** asked to fill every gap found in the comparison; `POST
  /investigations` was left out of the load test because of its daily cap and LLM cost.
- **Verification:** unit tests with a mocked HTTP transport; 1,200 requests against
  production, one error.

### Prompt revision and README

- **Task:** act on the failure analysis, and make the README as useful as the best
  submissions.
- **AI contribution:** four prompt rules (planner stays on the question's terms, follow a
  reference to its document, answer from combined facts, short abstentions); reran the
  evaluation and compared the prompts question by question (`make eval-prompts`); rewrote
  the README with Mermaid diagrams (system, ask flow, hybrid search, ingest), a real example
  answer, a decisions table and a documentation map. While checking failures, found that the
  evaluation records overwrote the gold answer with the system's answer and fixed it.
- **Author decisions:** spotted in the live demo that an abstention ("who won the 2034 World
  Championship?") listed 13 sources and started with "insufficient_evidence:", which started
  the revision; asked for the README to match the competitor's level of detail; kept the
  revised prompt in production after seeing equal correctness, fewer tokens and cleaner
  abstentions.
- **Verification:** 48-question rerun on the same model; `make api-check`, `make docs-check`.

### Moving the evaluation to Azure

- **Task:** finish the answer evaluation before the deadline after Groq's free daily quota
  stopped it.
- **AI contribution:** compared providers (Cerebras, Gemini, Groq paid tier, Bedrock) and
  walked through AWS quota requests; tested Azure's OpenAI-compatible endpoint with a plain
  and a forced tool call before switching; ran the full evaluation (agent, single-shot,
  cross-check); added the model comparison (`make eval-models`); switched production to
  Azure over SSH and verified it with a live question; wrote ADR-0010.
- **Author decisions:** found the Azure credit in the GitHub Student Developer Pack; chose to
  keep hosting on EC2 and move only the LLM; created the Azure project and deployment.
- **Mistakes caught:** the AI first proposed quota values below the Bedrock minimum, and the
  Hugging Face build of gpt-oss on Azure (managed GPUs) before the serverless model list was
  checked.
- **Verification:** 48 + 48 + 28 recorded answers; the live demo answers from Azure.

### Rate limit, prompt injection, cross-check, verifiable docs

- **Task:** prepare everything that didn't need LLM quota while the quota was used up.
- **AI contribution:** a daily cap per client IP and in total (`core/rate_limit.py`, 429) with
  uvicorn reading the client address behind Caddy; a Northwind document with a planted
  phishing instruction and three questions scored by an injection marker; an optional
  answer cross-check step; 9 ADRs with evidence (`docs/decisions/`), a requirements matrix
  (`docs/requirements.md`), and `scripts/check_docs.py` run in CI so documentation can't
  name a file, make target or ADR that doesn't exist.
- **Author decisions:** asked for a documentation pattern that can be verified rather than a
  large wiki; first stopped the rate-limit change, then kept it; asked that work continue
  without waiting for quota.
- **Mistakes caught:** CI found that the docs check flagged a git-ignored `.env` that exists
  only on a laptop; the check now skips ignored paths.
- **Verification:** unit tests for the quota, the injection metric and the cross-check;
  `make docs-check` locally and in CI.

### Investigation agent and answer evaluation

- **Task:** build `POST /investigations` and measure it.
- **AI contribution:** an OpenAI-compatible LLM client (timeouts, retries with capped
  backoff, `Retry-After`, a fallback model, `UpstreamError`); the agent (forced plan,
  parallel searches, a tool loop with a forced last turn); citation verification in code;
  the evaluation runner (48 questions, LLM judge from another model family, resumable JSONL,
  citation, abstention, contradiction and retrieval metrics); the chunking comparison; the
  evaluation report.
- **Author decisions:** set the goal of finishing the core in one day; tested the live agent
  with their own questions.
- **Mistakes caught:** in live use the model was offered several tools on the forced last
  turn and the API rejected it; uncited answers were turned into abstentions until the
  prompt and a send-back were added; a prompt example reused an evaluation question and was
  replaced with a fictional one; Qdrant Cloud needed a payload index the local Qdrant didn't.
- **Verification:** 107 tests at the time, `make api-check`, questions in the live demo.

## 2026-10-26

### Deployment

- **Task:** put the API online with persistence and HTTPS on free or credit-funded tiers.
- **AI contribution:** the Dockerfile with the embedding models baked in, a Compose file with
  Caddy, the EC2 bootstrap script and the GitHub Actions deploy workflow; step-by-step AWS
  console instructions; fixes for the GHCR push and the SSH setup.
- **Author decisions:** rejected Hugging Face Docker (paid) and Cloud Run (card hold), chose
  AWS EC2 as more professional; created the instance, Elastic IP and GitHub secrets; found
  that the production frontend still called `localhost`.
- **Verification:** the deploy workflow's health check; the live demo calls the API.

### Backend: ingestion, search, datasets

- **Task:** the document API, hybrid search and the 66k-document corpus.
- **AI contribution:** loaders for PDF, DOCX, Markdown and TXT with metadata; normalization
  and SHA-256 dedup; fixed and structure-aware chunkers; fastembed dense + BM25 embeddings;
  the Qdrant store; weighted RRF; the documents service and routes; HotpotQA and synthetic
  Northwind loaders; the retrieval evaluation that tuned RRF to k=10.
- **Author decisions:** agreed the five-endpoint API with the UI; reviewed a competitor's
  public repository and asked to beat it on quality; asked whether to use microservices
  and accepted the advice to stay with one service.
- **Verification:** integration tests against local Postgres and Qdrant; the retrieval
  evaluation over 200 questions.

## 2026-10-25

### Agent setup for the repository

- **Task:** make the repository work well with AI coding agents.
- **AI contribution:** wrote `AGENTS.md` (repo-wide and per app), `CLAUDE.md`,
  `.claude/settings.json` (allowed quality gates, denied `.env` reads and `git commit` /
  `git push`), a PostToolUse hook that formats edited files, two read-only subagents
  (`contract-guardian`, `convention-reviewer`) and three skills (`/check`, `/add-endpoint`,
  `/log-ai-usage`).
- **Author decisions:** asked for the agent setup; commits stay with the author, so the
  agent is blocked from committing.
- **Verification:** the hook was run against a Python file, a TypeScript file and an
  unrelated file; quality gates pass.

### Web app

- **Task:** build the frontend (`apps/web`) from the approved design, against a mocked API.
- **AI contribution:** scaffolded Vite + React + TypeScript + Tailwind; design tokens;
  shared UI components (floating-label text field, buttons, badges, confirm dialog);
  Investigate and Documents pages; TanStack Query hooks; MSW mocks; Vitest tests; CI.
- **Author decisions:** chose the stack direction and a single light theme in English;
  asked for the documents table to scroll inside the page instead of the window; asked to
  replace the browser's native confirm with a custom modal.
- **Verification:** lint, Prettier, type check, 7 unit tests and production build pass
  (`make web-check`).

### UI design

- **Task:** design the user interface before building it.
- **AI contribution:** produced a design canvas (Investigate, Documents, component states)
  and revised it through several iterations.
- **Author decisions:** cut features that went beyond the assignment and would have added
  backend work (progress tracking, document versions, filters, structured "affected
  services"); tried a single-page layout and went back to two pages; made dataset documents
  read-only while uploads stay editable.
- **Verification:** reviewed interactively on the canvas.

### Project foundation

- **Task:** review the starting skeleton and set up the repository.
- **AI contribution:** reviewed the existing FastAPI skeleton; restructured it into a
  monorepo (`apps/api`, src layout); tightened settings and error naming; added a Makefile
  and CI; explained each file.
- **Author decisions:** asked for a monorepo with consistent conventions across backend and
  frontend; set the working plan and deadline; decided to make commits personally.
- **Verification:** `make api-check` (ruff, mypy strict, pytest) passes; the server answers
  on `/health`.
