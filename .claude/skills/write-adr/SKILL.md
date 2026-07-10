---
name: write-adr
description: Write an Architecture Decision Record for a significant, already-made project-level decision. Use when CLAUDE.md's ADR rule triggers (a hard-to-reverse architecture, scope, or technology decision was just made) or when the user explicitly asks to record/write an ADR.
compatibility: Requires the `adr-tools` CLI (https://github.com/npryce/adr-tools). Install with `brew install adr-tools` if `which adr` fails.
metadata:
  author: yubarta
  version: "1.0"
---

Record one already-made, project-level decision as an ADR under `records/adr/`.

## When to use this

Only for decisions that are:
- **Already decided and, ideally, already implemented.** Do not write ADRs for planned future work (see `dev-docs/roadmap.md`); write the ADR when that stage is actually built, not before.
- **Project-level**, not stage-local: crosses capabilities, changes a structural pattern, or reverses a prior decision. A choice that only affects one stage's internal implementation belongs in that stage's `design.md` or `dev-docs/learnings/`, not a new ADR.

If unsure whether a decision clears that bar, ask the user rather than writing an ADR for something that's really just implementation detail.

## Always use `adr-tools`. Never hand-write the file.

Do not create the markdown file yourself with Write. The tool sets the date, the numbering, and the supersede/link cross-references correctly, things a hand-written file will get subtly wrong (wrong date, wrong link target, inconsistent "Superceded by" wording). If `adr` is not on PATH, install it first (`brew install adr-tools` on macOS) and confirm it succeeded before proceeding.

Since this runs non-interactively, prevent `adr new` from opening an editor and hanging:

```
EDITOR=true VISUAL=true adr new "Short Title Here"
```

`adr-tools` still opens `$EDITOR`/`$VISUAL` to fill in the ADR after creating it; `EDITOR=true` makes that a no-op (`true` exits immediately), so the command returns the new file's path on stdout instead of hanging. Fill in the content afterward with the Edit tool.

## Keep titles short

`adr-tools` derives the filename by slugifying the title text you pass to `adr new`, so a long title produces an unusable filename (this has already happened once in this project and had to be fixed). Titles should be **3-6 words**, naming the decision, not explaining it:

- Good: `"Capability-aligned architecture"`, `"Signal idempotency key"`, `"Standalone signal normalization"`
- Bad: `"Signal idempotency key is fingerprint plus fired_at, not fingerprint alone"` (too long, becomes an unreadable filename)

Put the nuance ("plus fired_at, not fingerprint alone") in the Context/Decision prose, not the title.

## Commands reference

- `adr new "Title"` — create a new, numbered ADR with the standard Nygard template (Status/Context/Decision/Consequences).
- `adr new -s N "Title"` — create an ADR that **supersedes** ADR number `N`. Inserts a link in the new ADR's Status section and automatically updates the old ADR's Status to `Superceded by [...]`. Use this whenever the new decision replaces a prior one; never hand-edit an old ADR's Status to mark it superseded.
- `adr link SOURCE LINK TARGET REVERSE-LINK` — link two ADRs that relate without one replacing the other (e.g. `adr link 5 Amends 3 "Amended by"`). Use when a decision refines or depends on another without invalidating it.
- `adr list` — list all ADRs in the directory.
- `adr generate toc` / `adr generate graph` — generate a table of contents or a relationship graph across all ADRs; useful if the user wants an index, not needed for writing a single ADR.
- `adr init [DIRECTORY]` — only for initializing a *new* ADR log from scratch. This project already has one (`records/adr/`, configured via `.adr-dir`); never run `adr init` here.

## Filling in the template

`adr new` produces placeholder text under Context/Decision/Consequences. Replace it with the real reasoning, not just the outcome:

- **Context**: what problem or tension prompted this, including the option(s) considered and rejected, if any. This is the part that stops the ADR from reading as an arbitrary edict.
- **Decision**: the actual choice, concrete enough that a future reader could tell whether code conforms to it.
- **Consequences**: split into what becomes easier, what becomes harder or riskier, and (if applicable) mitigations already in place for the risks. Do not skip the negative side; an ADR with only upsides reads as marketing, not a decision record.

Always explain the **why**, not just the **what**. "We use X" is not an ADR; "we use X because Y was rejected for Z reason" is.

## After writing

Cross-reference the new ADR from anywhere else that describes the same decision (e.g. `records/prd.md`, a stage's `design.md`) so the ADR is the durable source of truth and other docs point to it rather than restating it.
