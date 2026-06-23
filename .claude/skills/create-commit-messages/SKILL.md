---
name: create-commit-messages
description: Draft and create a conventional commit for staged or unstaged changes.
---

Write and create a git commit for the current changes following Conventional Commits.

**Steps**

1. Run `git status` and `git diff HEAD` to understand what changed.
2. Draft the commit message following the format below.
3. Show the message to the user and ask for confirmation before running `git commit`.
4. On confirmation, run `git commit -m "<message>"`.

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
