# AI usage log

A running record of how AI tools were used on this project, kept as the work happens. The
final AI Usage Report is written from these entries. Newest first.

**Tools:** Claude Code (Claude Opus 5.5) in VS Code — code generation, review, UI design on a
canvas, and explanations. Repository setup for agents: `AGENTS.md`, `CLAUDE.md` and
`.claude/` (permissions, a format-on-edit hook, review subagents, workflow skills).

Each entry: **Task** · **AI contribution** · **Author decisions** · **Verification**.

---

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
