@AGENTS.md

## Claude Code specifics

- `.claude/settings.json` allows the `make` quality gates, denies reading `.env` files and
  blocks `git commit` / `git push` — the author commits.
- A PostToolUse hook (`.claude/hooks/format-edited-file.mjs`) formats every file you edit
  with ruff or Prettier, so don't run formatters by hand after each edit.
- Subagents in `.claude/agents/`: `contract-guardian` (API contract drift between backend,
  frontend types and mocks) and `convention-reviewer` (repo conventions on a diff).
- Skills in `.claude/skills/`: `/check` (run gates, summarize failures), `/add-endpoint`
  (end-to-end endpoint workflow), `/log-ai-usage` (append to `docs/ai-usage.md`).
- After a meaningful AI-assisted change, offer to run `/log-ai-usage` — the AI Usage Report
  is a required deliverable.
