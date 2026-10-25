---
name: check
description: Run the quality gates (lint, format check, types, tests, build) for the apps changed in the working tree and summarize any failures with file:line and a proposed fix.
argument-hint: "[api|web|all]"
allowed-tools: Bash(make api-check), Bash(make web-check), Bash(git status:*)
---

Run the repository's quality gates — the same steps CI runs — and report the result.

1. Decide which apps to check:
   - `$ARGUMENTS` is `api`, `web` or `all` → use that.
   - Otherwise run `git status --short` and check each app with changes under `apps/api/` or
     `apps/web/`. If nothing changed, check both.
2. Run `make api-check` and/or `make web-check`. Run both even if the first fails.
3. Report:
   - One line per app: ✅ passed, or ❌ with the failing step (lint, format, types, tests, build).
   - For each failure: `file:line`, the error in one sentence, and the fix you propose.
     Group repeated errors of the same kind.
4. Don't fix anything unless asked. Never make a gate pass by disabling a rule, skipping a
   test or adding `# type: ignore` / `eslint-disable` / `any`.
