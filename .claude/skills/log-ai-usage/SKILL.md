---
name: log-ai-usage
description: Append an entry to docs/ai-usage.md describing what AI tools did in this session and what the author decided or changed themselves. Feeds the AI Usage Report deliverable.
argument-hint: "[short topic]"
---

Add one entry to `docs/ai-usage.md` for the work done in this session (topic: `$ARGUMENTS`
if given).

1. Read `docs/ai-usage.md` and follow the existing entry format exactly.
2. Draft the entry from what actually happened in this session:
   - **Task** — what was being built, in one line.
   - **AI contribution** — what the AI tool produced (code, design, review, explanations).
     Be specific: files or components, not "helped with the code".
   - **Author decisions** — choices the author made: requirements they set, suggestions
     they rejected or changed, corrections they asked for. Only list decisions visible in
     this session.
   - **Verification** — how the result was checked (tests, gates, manual run).
3. Show the draft and ask the author what they changed or decided themselves that you
   couldn't see. Never invent author contributions; if the author adds nothing, keep only
   what the session shows.
4. Append the approved entry under today's date (newest first). Don't commit.
