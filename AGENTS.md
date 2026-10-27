# Investigation Engine — agent guide

Instructions for AI coding agents working in this repository. Humans: see `README.md`.
App-specific rules live in `apps/api/AGENTS.md` and `apps/web/AGENTS.md`; read the one for the
app you are changing.

## What this is

A multi-hop, evidence-grounded RAG system. A user asks a question; an agent decomposes it,
searches a corpus of 50k+ documents with hybrid (semantic + keyword) retrieval, links facts
across documents, flags conflicting evidence, and answers with citations — or abstains when
the documents don't support an answer. It is a take-home assignment with a fixed list of
requirements, and the author must defend every line in a technical interview.

| Path | What |
|---|---|
| `apps/api` | Python 3.12 backend: FastAPI, Pydantic, managed with uv |
| `apps/web` | React 19 + TypeScript + Vite + Tailwind CSS 4, managed with pnpm |
| `docs/` | Decisions (ADRs), requirements matrix, evaluation report, AI usage log |
| `.claude/` | Claude Code settings, hooks, subagents and skills |

## Commands

Run everything from the repository root through `make` (`make help` lists all targets).

| Task | Command |
|---|---|
| Backend dev server (:8000) | `make api-dev` |
| Frontend dev server (:5173) | `make web-dev` |
| All backend gates (= CI) | `make api-check` |
| All frontend gates (= CI) | `make web-check` |
| Auto-format | `make api-format` · `make web-format` |
| Docs reference check (= CI) | `make docs-check` |

## Rules

1. **Scope is the assignment.** Build only what a requirement asks for. Before adding a
   feature, name the requirement it satisfies; if there is none, don't build it. Bonus items
   come after the core works, and only when asked.
2. **Done means green.** A change is finished when `make api-check` / `make web-check` pass
   for every app it touches. Never weaken a check (skip a test, add `# type: ignore`,
   `eslint-disable`, `any`) to get there without saying why.
3. **Don't commit or push.** The author commits. Finish with a Conventional Commit message to
   propose, e.g. `feat(api): add document upload endpoint`.
4. **Never read or print secrets.** `.env` / `.env.local` files are off limits. Settings come
   from environment variables via typed config (`core/config.py`, `shared/config/env.ts`).
5. **Consistency over cleverness.** Match the surrounding code: naming, file layout, error
   handling, comment density. One way to do each thing across the repo.
6. **Explainable code.** Prefer the obvious implementation. Comments say *why*, not *what*.
7. **Decisions have evidence.** Major design decisions are recorded in `docs/decisions/`
   (Context / Decision / Alternatives / Evidence). A change that contradicts an accepted
   decision adds a new ADR that supersedes it, with its own evidence. `docs/requirements.md`
   maps each assignment requirement to its code, tests and evidence: update it in the same
   change. `make docs-check` (also in CI) fails on a path, make target or ADR the docs name
   that doesn't exist.

## Cross-app contract

- **The API contract is shared.** Until OpenAPI type generation is wired up, the frontend
  types in `apps/web/src/features/*/types.ts` are the contract. A backend schema change must
  update those types and the MSW mocks in `apps/web/src/mocks/` in the same change.
- **JSON is camelCase on the wire**; Python stays snake_case internally (Pydantic aliases).
- **Errors** are always `{"error": {"code": "snake_case_code", "message": "Human sentence."}}`
  with a matching HTTP status. The message is shown to users as-is.
- **Endpoints:** `POST /investigations`, `GET /documents?search=&page=&pageSize=`,
  `POST /documents` (multipart `files`), `PUT /documents/{id}` (multipart `file`),
  `DELETE /documents/{id}`. Documents have `origin: "dataset" | "upload"`; dataset documents
  are read-only (`403`).

## Naming

| Thing | Convention | Example |
|---|---|---|
| Python modules, functions, variables | `snake_case` | `chunk_document()` |
| Python classes, Pydantic models | `PascalCase` | `UploadResult` |
| TS variables, functions, hooks | `camelCase`, hooks `useX` | `useDocuments()` |
| React components and their files | `PascalCase` | `DocumentTable.tsx` |
| Other TS files | `camelCase` | `queryClient.ts` |
| Booleans | `is` / `has` / `should` prefix | `isUploading` |
| Error codes | `snake_case` | `unsupported_format` |
