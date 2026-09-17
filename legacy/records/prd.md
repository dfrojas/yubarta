**Product Requirements Document (PRD)**

**Product Name:** Yubarta

**Key Concepts**

| Term | What it means |
|---|---|
| Signal | The single, normalized "something might be wrong (or might soon be)" event that enters Yubarta, no matter where it came from. Everything downstream works from a Signal, never from the original alert's raw format. |
| Reactor | The reactive input path: an external source (an alerting tool, an integrated vendor) tells Yubarta something fired or resolved. Yubarta listens for it; it doesn't go looking. |
| Scanner | The proactive input path: Yubarta periodically checks a target's health itself (disk space, memory, a custom check) and raises a Signal on an early warning sign, before something actually breaks. |
| Target | A specific host or service Yubarta knows how to reach and act on, including how to connect to it and which remediations are allowed there. |
| Remediation | A specific, pre-approved fix Yubarta is allowed to run (restart a service, rotate logs, flush a cache). Yubarta only ever runs remediations from this approved list, never something it invents in the moment. |
| Runbook | A written playbook: for a given kind of problem, what to check and which remediations usually fix it. This is what the diagnosis agent reads to make a decision. |
| Incident | The record of one specific problem, from the moment a Signal fires until it's resolved or escalated: what was tried, what happened, whether it worked. |
| Orchestrator | The part of Yubarta that drives the actual sequence: diagnose, try a remediation, check if it worked, retry or escalate. The AI proposes; the Orchestrator is what actually runs the show. |
| Diagnosis Agent | The AI component that looks at an Incident and its history, judges what's likely wrong, and picks the next remediation to try, always from the approved list. |
| Guardrail / Approval Gate | The safety check before anything risky happens: some remediations require a human to explicitly say yes before Yubarta runs them. |
| ChatOps | How a human talks to Yubarta and vice versa: asking questions, approving risky actions, getting notified when something happens. |
| Alert Cascade | When one root cause (e.g. a Spark executor OOM kill) trips independent alarms across several systems at once, so it looks like many separate problems instead of one. Diagnosing the real root cause instead of chasing each symptom separately is the hard version of Yubarta's job. |

**Objective:**
Yubarta is a self-hosted auto-remediation agent. A signal that a service is unhealthy (or trending toward unhealthy), from an external alert, an integrated observability vendor, or Yubarta's own periodic scanner, enters the system; an LLM agent diagnoses the problem from runbooks and past incidents, selects a deterministic remediation, executes it under audit, verifies recovery, retries with the next remediation if it did not, and escalates to a human once remediations are exhausted.

Learning applied AI (RAG, prompt caching, agent design, agent observability) and distributed-systems patterns (event queues, idempotent workers, long-running stateful processes) is a primary motivation for building Yubarta, but indirectly: the goal is to build something real end-to-end and understand every part of it, not to run isolated exercises or leave components scaffolded and abandoned.

**Pilot targets, and what "usable" actually means:**
- **Java VM, disk-filling log ingestion.** The first, simpler pilot case: a single Signal, a single obvious root cause, a low-risk idempotent remediation. This proves the loop mechanics end-to-end and stays a valid, real milestone, not a throwaway test.
- **Chaos-engineered Spark executor, alert-cascade root-cause diagnosis.** A replicated common Spark executor setup, with a chaos engineering plan that deliberately induces realistic failures (e.g. an OOM kill from an oversized partition), the same scenario a single root cause fans out into independent alarms across the orchestrator, compute engine, storage layer, and downstream systems. Yubarta has to find the actual root cause and fix it alone, not just react to one symptom in isolation.

The Spark scenario is the defining bar for the whole project, not a stretch goal. **Yubarta is not considered usable until it can diagnose and fix that scenario unattended.** Every feature, capability, and design decision should be weighed against whether it moves toward that bar; if it doesn't serve reaching it, it's not a priority yet, however useful it looks in isolation.

**Non-goals** (this document supersedes an earlier draft targeting a much larger platform; these are explicit exclusions, not oversights):
- Not a multi-tenant, horizontally-scalable SaaS platform today. No fleet orchestration, no multi-million-alarm throughput target. Kubernetes isn't ruled out for later; it's just not where the project starts.
- Not a language-agnostic remediation execution sandbox for arbitrary user code (Python/Go/Rust/C++ binaries). Remediations are a registered, deterministic MCP tool set, not user-submitted code in any language.

**Core safety principle (unchanged, foundational):** the AI diagnoses, selects, verifies, and reasons over data; deterministic code executes remediations and produces facts; humans gate destructive actions. The agent can never execute an action outside the registered set, and never fabricates a fact it could read from a tool. Detection is deterministic; the LLM is never in the detection path.

---

**1. Goals**

- Ingest and normalize externally-sourced alerts (reactive), integrated observability vendors, and Yubarta's own probe results (proactive) into one internal `Signal`, with idempotency.
- Integrate with observability vendors as additional signal sources, starting with Grafana, alongside the generic Alertmanager-format webhook that lets Yubarta work even with zero existing monitoring.
- Diagnose an incident with an LLM agent grounded in runbooks and past incident history (RAG), select a registered deterministic remediation, execute it, verify recovery, retry or escalate.
- Support a target with no existing monitoring at all. The proactive scanner is a first-class path, not a fallback for when reactive alerting is unavailable.
- Gate destructive actions behind human approval, delivered through ChatOps (Telegram/Slack).
- Persist incident history, remediation outcomes, and scanner sample windows to support reads, evals, and RAG over past incidents.
- Trace every LLM and tool call for cost and debugging (agent observability).
- Be genuinely reproducible and understandable end-to-end by one person, at every development stage: raise the stack, observe the capability actually working, not just green tests.

**2. User / persona**

Single persona: a solo operator (the author) running self-hosted services who wants leading-indicator detection and safe automated remediation, whether or not a monitoring stack already exists. A secondary "user" is future-self and any reader of the project's learning notes. The project is deliberately built to be legible as a teaching artifact, not just a working system.

**3. Functional requirements**

High-level only; the authoritative technical detail per capability lives in `dev-docs/yubarta-spec.md`, not duplicated here, to avoid two sources of truth drifting apart.

- Signal ingestion (reactive webhook, integrated vendors starting with Grafana, and proactive scanner), normalized into one internal `Signal`, idempotent.
- Target inventory: resolve a signal to a connectable target, its scan commands, and its credential reference.
- Deterministic remediation registry, exposed to the agent as MCP tools, each tagged destructive/idempotent/required-privilege.
- Remote execution over SSH, credentials resolved via SOPS + age at execution time, never inlined or logged.
- Diagnosis agent (Pydantic AI, LiteLLM tiered routing, RAG over runbooks/incidents, prompt caching of stable context).
- Remediation loop: an explicit, checkpointed state machine (`Received -> Diagnosing -> Remediating -> Verifying -> retry/Escalated/Resolved`), crash-resumable. A restart mid-remediation must resume, never blindly re-run a destructive action.
- Guardrails and gating: the agent's action space constrained to registered remediations; destructive actions require an approval gate.
- ChatOps interface: deterministic reads, deterministic actions, grounded-reasoning queries, escalations and approvals.
- Incident store (Postgres): incident history, remediation outcomes, retained scanner sample windows.
- Event/queue layer (Kafka): backs signal ingestion and internal event flow.
- Agent observability: LLM/tool-call tracing, token cost, per-step latency.
- Evaluation harness: replay recorded incidents, score whether the agent picked the correct diagnosis and remediation.

**4. Non-functional requirements**

- Targets a single host or a handful of nodes today; the event/queue layer (Kafka) is built on real distributed-systems patterns rather than a toy substitute, so the foundation isn't closed off from growing.
- Every side effect is auditable and executes with least-privilege, short-lived credentials.
- Crash-safe: state is persisted at each remediation-loop transition so a crash resumes rather than restarts.
- Cost-aware: tiered LLM routing and prompt caching, because this runs on a personal budget, not enterprise spend.
- Every architecturally significant decision is recorded as an ADR (`records/adr/`) and kept current. This PRD and the ADRs are living documents, not archival ones.

**5. Tech stack**

Python, Pydantic AI, LiteLLM, MCP, Postgres, Kafka, SOPS + age, Telegram/Slack, Docker Compose for local dev. Grafana as the first integrated observability vendor. RAG vector store is an open TODO, see `dev-docs/yubarta-spec.md`.

**6. Milestones**

Tracked live, stage by stage, in `dev-docs/roadmap.md`. Intentionally not restated here, to avoid this document drifting out of sync with the actual working plan.

**7. Risks & mitigations**

- **Scope creep back toward the original platform vision.** This PRD replaces an earlier draft that targeted 2M concurrent alarms, multi-tenant scale, and arbitrary-language remediation execution. Mitigation: any change that reintroduces that scope must flag the deviation explicitly as part of the project's decision-recording practice.
- **LLM cost outrunning a personal, single-subscription budget.** Mitigation: tiered LiteLLM routing, prompt caching, deliberate/bounded use of multi-agent workflows.
- **Destructive remediation causing real damage.** Mitigation: registered MCP tool set only, idempotency tagging, human approval gate via ChatOps, full audit trail.
- **Documentation (this PRD, the ADRs, the spec) silently going stale as the project evolves**, as happened to the previous version of this document. Mitigation: this PRD and the ADRs are treated as living documents, updated as part of normal development practice, not written once and left behind.

**8. Success metrics**

This is a learning project, so "success" isn't throughput or an SLA. It's:
- Each roadmap stage reaches a reproducible, demonstrable state (raised stack plus a checked-in driver script proving the capability works) before the next stage begins.
- The Java VM pilot case (disk-filling log ingestion) runs end-to-end: detect, diagnose, remediate, verify, without human intervention for the non-destructive path. This is a real, valid milestone, and the first proof the loop works, but it is not the finish line.
- **The defining success criterion**: Yubarta autonomously diagnoses and fixes a chaos-engineered Spark executor failure that has fanned out into an alert cascade across multiple systems, correctly identifying the actual root cause rather than reacting to one symptom. Until this works unattended, the project is not done, regardless of how many other capabilities are complete.
- A learning note exists per completed stage, and at least one is developed into an actual blog post or video.

---

*Supersedes the earlier platform-scale draft of this PRD (2M concurrent alarms, Datadog integration, multi-language remediation sandboxing). See [ADR-0003](adr/0003-capability-aligned-architecture.md) for the architectural decision this reflects.*
