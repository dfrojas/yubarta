---
name: create-commit-messages
description: Draft and create a conventional commit for staged or unstaged changes.
---

Write and create a git commit for the current changes following Conventional Commits.

**Steps**

1. Run `git status` and `git diff HEAD` to understand what changed.
2. Draft the commit message following the format below.
3. Re-read the draft line by line against every rule below and against the Anti-patterns section. Rewrite or delete any line that fails one. Do this before showing it, not after the user catches it.
4. Show the message to the user and ask for confirmation before running `git commit`.
5. On confirmation, run `git commit -m "<message>"`.

---

## Format

```
<type>[!](<subsystem>): <short summary>

<body>
```

Append `!` after the type (or subsystem) to signal a breaking change: `feat!:`, `refactor(api)!:`.

### type (required)

Pick the one that best describes the primary intent:

| type | when to use |
|------|-------------|
| `feat` | a new capability or user-visible behavior |
| `fix` | a bug correction |
| `refactor` | restructuring with no behavior change |
| `test` | adding or changing tests only |
| `docs` | documentation only |
| `chore` | tooling, deps, config, CI — no production code |
| `perf` | performance improvement |
| `style` | formatting, whitespace — no logic change |

### subsystem (optional but preferred)

The capability or module affected, in kebab-case. Use the folder name or domain term — e.g. `ingestion`, `signal`, `director`, `chatops`. Omit only when the change is truly cross-cutting.

### short summary (required)

- Imperative mood: "add", "remove", "fix", "introduce" — not "added" or "fixes"
- Lowercase after the colon
- No period at the end
- Max 72 characters for the whole first line

### body (include when the diff alone doesn't explain the why)

- Wrap at 72 characters
- Explain the motivation and context, not what the diff already shows
- Use plain prose or short bullet points
- Separate from the summary with a blank line
- Never use em-dashes (—); use a comma, colon, or rephrase instead
- Default to the shortest version that's still true. A one-paragraph body is normal, not a sign of insufficient effort.

## Anti-patterns

Real mistakes from past drafts, kept here as concrete negative examples because abstract guidance alone didn't prevent them.

- **Restating the diff as a list of what changed.** Bad: "Update every reference across CLAUDE.md, openspec config, README, and OpenSpec change artifacts to match." If `git diff --stat` already shows it, don't restate it in prose. State why the change was needed, not the mechanics of applying it.
- **Formulaic repetition.** Bad: three paragraphs in a row, each shaped "X was Y because Z." Vary sentence structure across paragraphs. Don't reuse the same reasoning connector (e.g. "because") in more than one paragraph.
- **Solution dressed up as motivation.** Bad: "needed a stronger, enforced bar," "written down anywhere durable." These describe the fix, not the problem that came before it. Motivation must describe what was wrong or missing beforehand. If a sentence would still make sense after deleting the diff, it's not motivation, it's a description of the change.
- **Padding.** Bad: "misleading scope judgment at the moments it mattered most," "quietly getting details wrong in ways that only surfaced later." Cut any adjective, qualifier, or clause that doesn't survive being deleted. If the sentence means the same thing shorter, use the shorter version.
