# Yubarta

Autonomous remediation agent for self-hosted infrastructure. Deterministic detection feeds an LLM that diagnoses an incident, picks a remediation from a registered MCP tool set, and executes it under audited, least-privilege control. Reactive (alerts) and proactive (periodic scans).

CRITICAL: DO NOT delegate tasks to subagents. Perform all work, file reading, and coding directly on the main thread.

Skills, rules, etc can be found in /.agents in the root of the repository.

## Chat Interactions
- Do not end our conversations with questions
- Do not add introductions in your responses like "apologies, my bad, you are right", etc. Always straight to the point
- Use ASD-STE100 Simplified Technical English when we talk

## Stack

Python + Pydantic AI (agent), LiteLLM (sole LLM proxy), MCP runtime (remediations as tools), Postgres (incident store), SOPS + age (secrets), Telegram/Slack (ChatOps). Queue and vector store TBD per spec.

## When you need more context, read only what applies

- Local dev rig (webhook simulator, fake Prometheus): `dev-docs/dev.md`
- Full project spec and capabilities backlog: `dev-docs/yubarta-spec.md`

## How to verify a change

- Tests: `make test`

## Universal rules

- Detection is deterministic. The LLM never decides whether something is wrong.
- All side effects go through the MCP remediation registry. No ad-hoc shell, no ad-hoc SSH.
- Credentials are resolved via SOPS + age at the boundary. Never inlined, never logged.
- Destructive remediations require ChatOps approval. Do not bypass the gate in code or tests.
- After completing an implementation change, emit a learning note in `dev-docs/learnings/` covering technical decisions, tradeoffs, and discoveries. Ask before writing it proposing the topics.
- Never use em-dashes, in any prose or documentation. Use a comma, parentheses, a period, or "and"/"but" instead.
- Significant, hard-to-reverse project-level decisions (architecture, scope, technology choice) get recorded as an ADR under `records/adr/` using `adr-tools` (`adr new "<title>"`), not just discussed and left to live only in conversation or memory. This applies any time such a decision is made, wether during an explore session, or ad-hoc conversation. Reversing or replacing a prior decision means a new ADR that marks the old one Superseded, never silently editing or ignoring it.
