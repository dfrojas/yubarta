# Yubarta — Project Specification (v8, definitive)

# Yubarta (v8 — definitive)

> This is the definitive, cumulative spec. It carries forward everything agreed in v1–v7; older versions are kept only as history and need not be read. New in v8: scan probes are simplified to a plain **list of commands** — the user declares no transport or mode; Yubarta infers periodic vs streaming by whether the process exits or stays alive; HTTP scraping is just a `curl` command.

## Purpose

Yubarta is a self-hosted auto-remediation framework. A signal that a service is unhealthy (or trending toward unhealthy) enters the system; an LLM agent diagnoses the problem from runbooks and past incidents, selects and runs a deterministic remediation, verifies whether the service recovered, retries with the next remediation if it did not, and escalates to a human once remediations are exhausted.

A defining design goal: Yubarta must work for a small service with **no monitoring stack at all** — no Prometheus server, no paid alerting product. The pilot is one real Java service on a small VM with no alerting today.

This is a learning project, not a product. The goal is to learn applied AI techniques (RAG, prompt caching, agent design, agent observability) and distributed-systems patterns (event queues, idempotent workers, long-running stateful processes). Some components are deliberately left thin so they are built and understood rather than scaffolded fully — marked `TODO`.

Core safety principle, fixed: **the AI diagnoses, selects, verifies, and reasons over data; deterministic code executes remediations and produces facts; humans gate destructive actions.** The agent can never execute an action outside the registered set, and never fabricates a fact it could read from a tool. Read-only by default. Detection is deterministic; the LLM is never in the detection path.

## Input Model — two core modes, one loop

Both modes are first-class (neither is optional) and normalize into the same internal signal that feeds the remediation loop:

- **Reactive.** An external alerting source POSTs to a generic webhook (reference format: Alertmanager firing/resolved; Prometheus + Alertmanager is the open-source example). No vendor is assumed. In dev this is **simulated**: a bash script / curl posts real Alertmanager-format firing/resolved payloads (fixtures) to Yubarta's endpoint — no real service is built. Optionally, the full Prometheus + Alertmanager chain can be run against the fake exporter for end-to-end realism, but the default is to simulate the payload.
- **Proactive / self-monitoring (default for unmonitored services).** Yubarta's own deterministic **scanner** periodically probes a target, evaluates thresholds, retains a rolling window of samples, and emits internal signals. This lets it act on **leading indicators** (disk at 80% before 100%, memory trending up, pool near saturation) before user impact. "Before the user" means acting on leading indicators, not prediction.

### Scan probes

A probe is just a command — any Linux command, k8s-exec style. Yubarta runs it and infers how to treat it:

- If the process **exits**, it is periodic: Yubarta re-runs it on the scan interval, capturing stdout/exit code.
- If the process **stays alive and emits** (e.g., `fswatch`, `tail -f`), it is streaming: Yubarta consumes the stream and manages its lifecycle, restarting it if it dies.

The user declares nothing about mode or transport — Yubarta knows. To scrape an HTTP metrics endpoint, the command is simply `curl`.

Detection parsing stays deterministic — the scanner never uses the LLM to read a value. Prefer structured output (`df --output=pcent`, `/proc/meminfo`) over parsing human-formatted output; if parser maintenance is the concern, the LLM may be used **offline** to generate a parser that deterministic code runs at runtime. Probes are declared in config and read-only.

## ChatOps — human control surface

A Telegram/Slack interface for the human in the loop. It is a thin natural-language layer: the agent parses intent and routes to one of three categories. It never grants the LLM free control of the infrastructure.

- **Deterministic reads (facts).** The agent parses the question, calls a deterministic tool, and formats the answer — it never invents the value. Examples: "which remediation fixed the last crash?" (incident history), "CPU usage for the last hour on service X" (metrics window), "how much disk is free on the VM?" (a probe), "is the service okay?" (status read).
- **Deterministic actions.** The agent parses intent; the action is deterministic and authenticated. Example: approving a remediation marked escalate-to-human (the approval gate). A human may also issue arbitrary commands here (kubectl-exec style), authenticated and audited, bounded by the least-privilege SSH user.
- **Grounded reasoning.** The one place the LLM earns its place. Example: "will it fail in the next hour given the data?" A judgment over retained trends, leading indicators, and past incidents (RAG) — it must show the data and the reasoning, not emit a number with no basis. For simple single-signal cases (e.g., disk fill rate), a deterministic extrapolation is preferred; the LLM adds value when multiple signals interact and the pattern is non-obvious.

ChatOps is also where escalations land and where gated approvals are requested and answered.

## Tech Stack

- **Language / runtime:** Python
- **Signal sources:** generic alert webhook (core; Alertmanager format) + internal scanner (any command; run-mode inferred)
- **ChatOps:** Telegram or Slack bot, mapping commands to deterministic operations and grounded-reasoning queries
- **Queue / event layer:** a log/queue for incoming signals. `TODO:` Kafka vs something lighter — Kafka is justified only if you want to learn its internals; for a single self-monitored node it may be overkill. Decide whether it is there for learning or for need.
- **Data stores:** Postgres for incident state, checkpoints, and incident history (decided); plus a rolling window of scanner samples. `TODO:` retention-window length.
- **Agent framework:** Pydantic AI
- **LLM access:** LiteLLM as the single proxy, tiered routing (cheap model for classification/verification, larger for novel diagnosis)
- **Tool exposure:** MCP — remediations and deterministic reads exposed to the agent as MCP tools
- **Remote execution:** SSH against targets, driven by `inventory.yaml`
- **Secrets:** SOPS + age — credentials referenced from the inventory, resolved at execution, never inline
- **RAG store:** `TODO:` pick deliberately; retrieval quality is a learning target
- **Agent observability:** LLM/tool-call tracing (token cost, per-step latency, tool-call traces). `TODO:` choose the approach
- **Dev environment:** a webhook simulator (script/fixtures posting Alertmanager-format payloads) for the reactive path, and a controllable fake Prometheus exporter (minimal `prometheus_client`, or grafana/fake-metrics-generator / filippog/fake_exporter) for the proactive path; both drivable into bad states on demand; docker-compose for the breakable test setup. No real test service is built.

> The earlier MVP may contain reusable plumbing (ingestion, queue, persistence, a Director). Treat its README/blog as stale — verify against current code before reusing anything.

## Project Conventions

### Architecture Patterns

- A deterministic **orchestrator** (the role the MVP "Director" played) owns the remediation state machine and calls the agent as a step. The agent is never the driver.
- The remediation loop is an explicit state machine: `Received → Diagnosing → Remediating → Verifying → (retry | Escalated | Resolved)`. State is persisted at each transition so a crashed run **resumes** instead of restarting — re-running a destructive remediation is the failure to avoid. Record an execution before it runs (idempotency key), not after.
- "Done" means the original condition cleared (a `resolved` from the same source, or the scanner confirming the metric is back in range), not a single local health check passing. A self-recovery `resolved` can preempt an in-flight loop.
- Remediations are deterministic, idempotent units. The agent selects one; it does not author it. The agent never runs commands extracted from LLM output autonomously.
- **Deterministic vs LLM split for command output.** In detection, the scanner reads values with deterministic parsers or structured command output — never the LLM. The LLM reads unstructured output only in the diagnosis path: when the agent investigates an active incident and hits free-form evidence (application logs, `dmesg`, stack traces, odd errors), it reasons over that text. Different frequency, stakes, and data shape than detection.
- Facts in ChatOps come from deterministic tools, never from the model, except for grounded-reasoning queries, where the model reasons over retained data and must show its basis.
- Stable prompt context (system description, tool definitions, retrieved runbook) is cached across the many LLM calls in one incident.
- Reactive and proactive modes share everything downstream of signal normalization.
- The human approval gate is delivered through ChatOps.

### Testing Strategy

- Two dev simulators are the primary drivers: a webhook simulator for the reactive path (POST Alertmanager-format fixtures) and a controllable fake exporter for the proactive path. Push either into a bad state, watch the loop diagnose, remediate, and verify recovery.
- An eval harness replays recorded incidents and checks the agent picked the correct diagnosis and remediation. `TODO:` design the harness yourself.

### Code Style / Git Workflow

`TODO:` note your conventions once.

## Domain Context

- A **runbook** is a structured document: symptoms, diagnosis steps, and an ordered list of remediations. Runbooks plus past incidents are the RAG corpus.
- A **signal** is normalized internally with: a `status` (firing/resolved or scanner equivalent), an identity (labels + a stable fingerprint), the source (external alert vs internal scan vs ChatOps), and metadata. Threshold evaluation lives in the source (external system, or Yubarta's deterministic scanner) — never in the LLM.
- **Retained data.** To answer history, trend, and forecast queries, Yubarta retains the incident history (what happened, which remediation, the outcome) in Postgres, and a rolling window of scanner samples. The scanner's job is evaluate-threshold **and** retain-window, not evaluate-and-discard.

Seed incidents:

- **Disk-filling log ingestion (real pilot case, proactive).** A log ingestion fills the VM disk and blocks DB writes; today it is flushed manually. The scanner watches disk usage (a `df` command, which Yubarta runs periodically, and/or `fswatch` on the log directory, which Yubarta consumes as a stream) and fires on a leading indicator (e.g., 80%) before the disk fills; the remediation rotates/flushes/archives the logs safely (never blind-deletes); verify disk is back below threshold. Low-risk and idempotent, so it likely needs no human gate — the ideal first end-to-end remediation. (Honest note: the AI adds little here; the cause and action are obvious. It validates the loop; the AI's value shows up on non-obvious causes.)
- Redis cluster down → restart/diagnose → verify.
- Database refusing writes because full → flush cache → verify → report.

These are starting cases; the remediation set grows and must not collapse the framework's identity into them.

## Target Inventory

The inventory answers where to connect and how, for remediations and host-level diagnostics/scans. Config Yubarta reads, separate from signals and from the agent. Connection metadata lives here; secrets do not — referenced and resolved from SOPS + age at execution. A signal's labels are matched against target labels to resolve which target to act on; the per-target `remediations` list is a second guardrail on top of the registry.

```yaml
# inventory.yaml
groups:
  ssh-defaults:
    transport: ssh
    user: yubarta
    port: 22

targets:
  java-app-1:                # the pilot VM
    group: ssh-defaults
    address: 10.0.0.20
    labels:
      service: java-app
      role: api
    scan:
      interval: 30s          # used to re-run commands that exit
      commands:              # any Linux command; Yubarta infers periodic vs streaming
        - run: "df --output=pcent /var | tail -1"
          as: disk_usage
        - run: "fswatch /var/log/app"            # stays alive → streamed
        - run: "curl -s localhost:8080/actuator/prometheus"
      checks:
        - disk_usage > 80%    # leading indicator for the log-ingestion case
    credential: sops://secrets/hosts/java-app-1.yaml#ssh_key
    remediations:
      - rotate-and-flush-logs # safe: rotate/archive/truncate, never blind delete
      - restart-java-app

  redis-cache-1:
    group: ssh-defaults
    address: 10.0.0.5
    labels:
      service: redis
      role: cache
    credential: sops://secrets/hosts/redis-cache-1.yaml#ssh_key
    remediations:
      - restart-redis
      - flush-redis-cache
```

`TODO (learning gaps):`
- Label-matching from signal → target is unspecified. Decide the rules and what happens on ambiguous/no match (escalate, do not act blindly).
- Credential reference resolution (`sops://...`) is a sketch. Define resolution to a short-lived, least-privilege credential at execution, and how each use is audited.
- Value extraction (`as:`) and thresholds: how a command's output maps to a named value, where thresholds live, how leading-indicator conditions are expressed, and the sample-window length. Keep extraction deterministic.

## Important Constraints

- Single host / few nodes. No fleet orchestration, no Kubernetes. No required external monitoring or alerting product.
- Destructive remediations require an explicit gate (human approval via ChatOps, or a policy allowlist) before execution.
- The agent never runs arbitrary commands extracted from LLM output autonomously. Arbitrary commands are allowed only when a human issues or approves them.
- ChatOps commands are authenticated and restricted to authorized users; deterministic reads/actions map only to the fixed set of operations, and reasoning queries must show the data they are based on.
- Runtime guardrails constrain the agent's action space to registered remediations; a hallucinated action must be impossible to execute. The inventory's per-target `remediations` list is an additional constraint.
- Scan commands are declared in config and read-only; Yubarta infers run-mode; detection never depends on the LLM.
- Remediation tools run with scoped, short-lived, least-privilege credentials from SOPS + age. Every action is audited.
- Every LLM call and tool call is traced for cost and debugging.
- eBPF signal, if used, enters as an external input from eBPFluga — not embedded in Yubarta.

## External Dependencies

LiteLLM, Pydantic AI, MCP server runtime, SOPS + age, Postgres, the chosen vector store, the chosen queue, a Telegram/Slack bot SDK; for dev, a webhook simulator and a fake Prometheus exporter.

## Capabilities

The spec backlog, as independent capabilities (order is your call):

- `signal-ingestion` — normalize external alerts (webhook, core), internal scans, and ChatOps requests into one internal signal, with idempotency
- `proactive-scanner` — run user-declared commands (periodic vs streaming inferred by Yubarta), threshold + leading-indicator evaluation, retention of a rolling sample window, emit signals
- `target-inventory` — `inventory.yaml`: resolve signal → target, connection method, scan commands, credential references
- `remediation-registry` — deterministic remediations as MCP tools, each tagged (destructive?, idempotent?, required privilege)
- `remote-execution` — execute a remediation over SSH against an inventory target
- `diagnosis-agent` — agent + RAG over runbooks/incidents; reads unstructured evidence with the LLM; tiered LLM routing; prompt caching of stable context
- `remediation-loop` — orchestrator-driven state machine: select → execute → verify → retry → escalate, with checkpointed state
- `guardrails-and-gating` — constrain the action space; gate destructive actions (approval delivered via ChatOps)
- `chatops-interface` — Telegram/Slack: deterministic reads, deterministic actions, grounded-reasoning queries, escalations
- `incident-store` — persist incident history and outcomes in Postgres to support reads, evals, and RAG over past incidents
- `agent-observability` — tracing of LLM/tool calls, token cost, per-step latency
- `evaluation-harness` — replay recorded incidents, score the diagnosis and remediation choice

Intended learning surfaces: `diagnosis-agent`, `agent-observability`, `evaluation-harness`, the RAG-store choice, and the inventory/scanner `TODO`s. Spec the interface; keep the implementation thin enough that you build the interesting part yourself.
