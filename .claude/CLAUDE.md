# Yubarta

Autonomous remediation agent for self-hosted infrastructure. Deterministic detection feeds an LLM that diagnoses an incident, picks a remediation from a registered MCP tool set, and executes it under audited, least-privilege control. Reactive (alerts) and proactive (periodic scans).

## Stack

Python + Pydantic AI (agent), LiteLLM (sole LLM proxy), MCP runtime (remediations as tools), Postgres (incident store), SOPS + age (secrets), Telegram/Slack (ChatOps). Queue and vector store TBD per spec.

## When you need more context, read only what applies

- Architectural invariants and gating: `docs/architecture.md`
- MCP remediation tool contract: `docs/remediations.md`
- Diagnosis agent and RAG layout: `docs/diagnosis-agent.md`
- Inventory and credential resolution: `docs/inventory.md`
- Local dev rig (webhook simulator, fake Prometheus): `docs/dev.md`
- Full project spec and capabilities backlog: `docs/yubarta-spec.md`

## How to verify a change

- Tests: `make test`
- Types: `make check`

## Universal rules

- Detection is deterministic. The LLM never decides whether something is wrong.
- All side effects go through the MCP remediation registry. No ad-hoc shell, no ad-hoc SSH.
- Credentials are resolved via SOPS + age at the boundary. Never inlined, never logged.
- Destructive remediations require ChatOps approval. Do not bypass the gate in code or tests.
- After completing an OpenSpec change, emit a learning note in `docs/learnings/` covering technical decisions, tradeoffs, and discoveries.

