# Yubarta Refactor Roadmap

One OpenSpec change per stage. Each change must leave the system runnable before moving to the next.

## Stages

| # | Change name | Capability | Status |
|---|---|---|---|
| 0 | `cleanup-and-foundation` | structural cleanup + canonical Signal model | done (2026-06-05) |
| 1 | `signal-ingestion` | generic Alertmanager webhook, normalize to Signal, idempotency | done (2026-06-23) |
| 2 | `target-inventory` | inventory.yaml schema + loader, label matching | done (2026-07-10) |
| 3 | `incident-store` | Postgres schema for state machine lifecycle + remediation outcomes | in progress |
| 4 | `remediation-loop` | orchestrator state machine, checkpointed (Received→Diagnosing→Remediating→Verifying→retry/Escalated/Resolved) | not started |
| 5 | `remote-execution` | SSH wired to loop, SOPS credential resolution, audit trail | not started |
| 6 | `proactive-scanner` | probe runner, periodic vs streaming inference, threshold eval, rolling window, emit Signal | not started |
| 7 | `remediation-registry` | MCP tool wrappers, destructive/idempotent tagging, per-target guardrail | not started |
| 8 | `diagnosis-agent` | Pydantic AI agent, RAG over runbooks/incidents, LiteLLM tiered routing, prompt caching | not started |
| 9 | `guardrails-and-gating` | action space constraint, destructive gate, approval flow | not started |
| 10 | `chatops-interface` | Telegram/Slack bot, deterministic reads, deterministic actions, grounded-reasoning queries, escalations | not started |
| 11 | `agent-observability` | LLM/tool-call tracing, token cost, per-step latency | not started |
| 12 | `evaluation-harness` | incident replay, diagnosis and remediation scoring | not started |
| 13 | `multi-target-correlation` | correlate Signals from different Targets into one Incident (alert-cascade root cause: one root cause tripping alarms across an orchestrator, a compute layer, storage, and a downstream app) | not started |
