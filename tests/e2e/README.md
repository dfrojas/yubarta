# Automated product E2E tests

These tests run the installed `yubarta serve` process with scenario YAML. They
observe the Control API, CLI, and a real Java HTTP service. PostgreSQL and SSH
are real. In-process component tests live in `tests/integration/`.

## Run

Requires Python 3.12+, a running Docker engine, and PostgreSQL's `initdb` and
`pg_ctl` on PATH. Alternatively set `YUBARTA_TEST_POSTGRES_URL` to a dedicated
test PostgreSQL admin URL whose user can create/drop databases. Never use the
manual lab or production database.

```sh
python -m pip install -e ".[dev]"
python -m pytest tests/e2e -q
```

The harness builds `scenarios/java` once per session, allocates loopback ports,
starts one container and product process per test, and uses a fresh database.
Cleanup removes containers and the session image tag; build cache is retained.
Product logs are stored in pytest's temporary directory and included with target
state and API observations in failure reports.

## Coverage and limits

- Apply: kill the JVM, ingest a synthetic AJP log line, run diagnostics, try the
  configured remediations, verify HTTP recovery and a new Java PID, inspect the
  resolved incident through the API and CLI.
- Dry-run: inject the same fault, verify recorded skipped remediations and that
  the application stays down during a bounded observation window.
- `ensure-swap` only inspects memory. `fix-tomcat-restart-policy` only records
  intent in a file. Only `restart-app` restores the service. The names preserve
  the original ordered-remediation scenario; no Tomcat/systemd behavior is proven.
- The log is written by the test, not Apache. SIGKILL does not simulate actual
  memory exhaustion. These are fast automated workloads, not production replicas.

Cold Docker builds have a separate five-minute budget. After build, each case
normally finishes in seconds; startup, recovery, operations, and teardown have
bounded waits. No test accesses `sandbox/Java`, the independent manual lab.

The optional `scenarios/java/docker-compose.yaml` is for debugging this automated
target only. It uses dynamic ports; inspect them with `docker compose ... port`.
The pytest suite manages its own resources and does not use this Compose project.
