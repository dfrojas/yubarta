# 3. Capability-aligned architecture

Date: 2026-07-10

## Status

Accepted

Supercedes [2. Design Patterns](0002-design-patterns.md)

## Context

ADR 0002 committed to a hybrid DDD + Hexagonal + Plugin architecture (`yubarta/core`, `yubarta/drivers`, `yubarta/entrypoints`, `yubarta/controllers`) for a much larger platform vision: a horizontally-scalable, multi-tenant automation platform supporting up to 2 million concurrent alarms, third-party monitoring integrations (Datadog), and user-submitted remediation code in any language.

The project's actual scope narrowed significantly (see `records/prd.md` and `dev-docs/yubarta-spec.md`, the definitive spec): a self-hosted auto-remediation agent for a single host or a handful of nodes, explicitly a learning project rather than a product, with remediations restricted to a registered, deterministic MCP tool set rather than arbitrary user-submitted code. The old codebase under the ADR-0002 architecture (`old/`, a Rust director, a frontend) had a broken entrypoint, two conflicting Alert models, and dead code, and was deleted wholesale in the `cleanup-and-foundation` stage.

A strict layered architecture (Hexagonal + DDD + Plugin) adds structural overhead that isn't justified at this scale, and doesn't reflect how the codebase is actually organized: around the spec's independent, roughly-one-OpenSpec-change-each capabilities (signal-ingestion, proactive-scanner, target-inventory, remediation-loop, etc.).

## Decision

Replace the Hexagonal/DDD/Plugin architecture with capability-aligned top-level modules, one per capability:

- `yubarta/ingestion/`: webhook + scanner adapters, both normalize to `Signal`
- `yubarta/scanner/`: probe runner, rolling window, threshold evaluation
- `yubarta/orchestrator/`: remediation state machine (the role the old "director" played)
- `yubarta/agent/`: diagnosis, RAG, LiteLLM routing
- `yubarta/chatops/`: Telegram/Slack bot
- `yubarta/infra/`: shared low-level drivers (db, ssh, cache, messaging, secrets)
- `yubarta/domain/`: canonical shared models (`Signal`, `Incident`)

Not strict Hexagonal. Protocol interfaces are used only at three real seams: storage, messaging, SSH, not as a blanket pattern across every component. Integration tests against real/containerized infrastructure are preferred over extensive unit-test fakes, matching how production ops services are actually tested, rather than leaning on unit-test fakes everywhere.

The canonical internal type is `Signal`, not `Alert`; source-specific fields (e.g. Kafka lag, Confluent consumer group) stay in the ingestion adapter and never cross into `domain/`.

Rule of thumb for where shared code lives, clarified during `cleanup-and-foundation`: if only one capability uses a piece of infrastructure (a DB session helper, a client wrapper), it lives inside that capability's own folder. If two or more capabilities use it, it moves to `infra/`. This is not a new decision, it is the operational detail that makes the capability-aligned layout above actually work in practice.

Non-negotiable invariants carried forward regardless of architecture (unchanged from the project's core safety principle): detection is deterministic and the LLM is never in the detection path; all side effects go through the MCP remediation registry; credentials resolve via SOPS + age at the boundary and are never inlined or logged; destructive remediations require a ChatOps approval gate.

## Consequences

### Positive
- Structure matches how the spec is organized and how the roadmap sequences work: one OpenSpec change per capability, each leaving the system runnable.
- Less boilerplate and indirection than a full Hexagonal/DDD/Plugin stack; easier for a solo learner to hold the whole system in their head at once.
- Protocol seams stay where they earn their cost (storage/messaging/SSH), not scattered everywhere out of habit.

### Negative
- Less structurally-enforced separation than strict Hexagonal. Keeping infra concerns out of `domain/` relies on convention (this ADR, `CLAUDE.md`, code review) rather than the architecture forcing it.
- Revisiting this if the project ever grows toward genuine multi-tenant/horizontal scale would mean reintroducing more structure later, accepted as unlikely given the PRD's non-goals.

### Mitigations
- `records/prd.md`'s non-goals section and `openspec/config.yaml`'s `rules.proposal` flag any scope creep back toward the old platform vision, the actual condition that would justify revisiting this decision.
