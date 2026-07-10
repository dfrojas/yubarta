# Yubarta

Autonomous remediation agent for self-hosted infrastructure. Deterministic detection feeds an LLM that diagnoses an incident, picks a remediation from a registered MCP tool set, and executes it under audited, least-privilege control. Reactive (alerts) and proactive (periodic scans).

CRITICAL: DO NOT delegate tasks to subagents. Perform all work, file reading, and coding directly on the main thread.

## Stack

Python + Pydantic AI (agent), LiteLLM (sole LLM proxy), MCP runtime (remediations as tools), Postgres (incident store), SOPS + age (secrets), Telegram/Slack (ChatOps). Queue and vector store TBD per spec.

## When you need more context, read only what applies

- Architectural invariants and gating: `dev-docs/architecture.md`
- MCP remediation tool contract: `dev-docs/remediations.md`
- Diagnosis agent and RAG layout: `dev-docs/diagnosis-agent.md`
- Inventory and credential resolution: `dev-docs/inventory.md`
- Local dev rig (webhook simulator, fake Prometheus): `dev-docs/dev.md`
- Full project spec and capabilities backlog: `dev-docs/yubarta-spec.md`

## How to verify a change

- Tests: `make test`
- Types: `make check`

## Universal rules

- Detection is deterministic. The LLM never decides whether something is wrong.
- All side effects go through the MCP remediation registry. No ad-hoc shell, no ad-hoc SSH.
- Credentials are resolved via SOPS + age at the boundary. Never inlined, never logged.
- Destructive remediations require ChatOps approval. Do not bypass the gate in code or tests.
- After completing an OpenSpec change, emit a learning note in `dev-docs/learnings/` covering technical decisions, tradeoffs, and discoveries.
- Never use em-dashes, in any prose or documentation. Use a comma, parentheses, a period, or "and"/"but" instead.
- Significant, hard-to-reverse project-level decisions (architecture, scope, technology choice) get recorded as an ADR under `records/adr/` using `adr-tools` (`adr new "<title>"`), not just discussed and left to live only in conversation or memory. This applies any time such a decision is made, whether during an OpenSpec design phase, an explore session, or ad-hoc conversation. Reversing or replacing a prior decision means a new ADR that marks the old one Superseded, never silently editing or ignoring it.

