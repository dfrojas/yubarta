# Yubarta V1

A single Python process monitors one Linux host over SSH. Matching events create
persisted incidents. Each incident runs diagnostics, health prechecks, ordered
remediations, and independent verification. Only passing **all** checks resolves
an incident. The timeline identifies the remediation followed by recovery.

## Run

Requirements: Python 3.12+, Poetry 2.2.1, PostgreSQL, and an SSH-accessible Linux
target. The control host must also reach the configured HTTP health endpoint.

```sh
poetry install
cp .env.example .env
# Set the values in .env. Use a dedicated PostgreSQL database and SSH identity.
set -a
. ./.env
set +a
poetry run yubarta serve --config config.example.yaml
```

Dry-run is the default. It scans, records incidents, executes diagnostics and
checks, and records skipped remediation steps. Apply mode is explicit:

```sh
poetry run yubarta serve --config config.example.yaml --apply
poetry run yubarta health
poetry run yubarta status
poetry run yubarta scanners
poetry run yubarta incidents
poetry run yubarta incident <incident-id>
```

`YUBARTA_DATABASE_URL` uses `postgresql+asyncpg://...`. Alembic migrations run at
daemon startup. `YUBARTA_API_TOKEN` is read by both the daemon and CLI. Set a
non-empty token for deployment. Environment placeholders in YAML are expanded
after YAML parsing. Missing or empty required values stop startup.

The CLI uses HTTP only. The API provides `/health`, `/status`, `/scanners`,
`/incidents`, and `/incidents/{id}`. Administrative routes are also available
under `/api/v1`; OpenAPI is at `/docs`. A public bind requires a token. The default
bind is loopback. Use an SSH tunnel for remote access:

```sh
ssh -L 8787:127.0.0.1:8787 yubarta-control
poetry run yubarta --server http://127.0.0.1:8787 status
```

## Configuration and execution

See [config.example.yaml](config.example.yaml) and [architecture](docs/architecture.md).

- `watch.log`: remote `tail -n <backfill> -F`, reconnect and replay deduplication.
- `watch.command`: a stream when `interval` is absent; periodic execution otherwise.
- `expect.exit_code` on a **watch** is a trigger. `systemctl is-failed` returns 0
  when the service has failed. On a **check**, the expectation means healthy.
- `match_any` and `match_all` apply to the normalized message. Watches default to
  incident type `tomcat-unavailable`; set `incident_type` for other failures.
- `parser.kind` accepts `text`, `json`, or `regex` (with `pattern`). Named regex
  groups and JSON keys can supply `message`, `level`, and ISO `timestamp`.
  `parser.multiline: true` joins Java stack trace continuations; idle buffers
  flush after `parser.flush_after` (default 300 ms).
- HTTP `auth.bearer_from_env` and `auth.headers_from_env` load secrets at startup.
  Response bodies and authentication headers are not recorded.
- `verify` controls settle delay, polling interval, and timeout after **each**
  executed remediation. A failed command can still be followed by healthy checks.
- A `required: true` remediation stops the plan if it cannot be executed, such
  as an SSH error or timeout. Normal nonzero exits still receive verification.
- Diagnostics are best effort. A healthy precheck resolves without remediation
  and leaves `resolved_by_step_id` null. An unhealthy dry-run ends as `FAILED`
  with an explicit dry-run reason, never as a false recovery.

## Tests

```sh
poetry run pytest tests/unit -q
poetry run pytest tests/integration -q
poetry run pytest tests/e2e -q
# All layers together:
poetry run pytest -q
```

Integration and E2E tests require Docker with Compose and at least 3 GB free
space. Fixtures create isolated PostgreSQL databases, temporary SSH keys, trusted
host keys, random loopback ports, and a Compose project. They remove the test
containers and volumes on completion. No test skips missing dependencies.

The sandbox runs real OpenSSH and a real HTTP service. It models systemd commands
and kernel swap activation so tests do not change the Docker host's swap. The
production remediation scripts run unchanged: they allocate and format a real
2 GiB swap file, update `fstab`, write a systemd drop-in, and check effective
policy. Tests inject failure, follow logs over SSH, query the API and CLI, prove
recovery attribution, disconnect SSH, replay backfill, and send SIGTERM.

## Deploy through Ansible

Use existing Debian/Ubuntu target and control hosts. The control host needs
Python 3.12+ and access to a PostgreSQL database owned by the configured role.
The target needs the `tomcat9` systemd service. Adjust the example checks and
diagnostics for the host's installed PostgreSQL version and log locations.

1. Build the wheel. Copy `infra/ansible/inventory.example.yaml` to a private
   inventory outside this repository and set both host addresses.
2. Supply paths to the environment file, dedicated SSH key pair, and verified
   `known_hosts` file using the inventory variables shown in the example.
3. Set the environment paths to `/etc/yubarta/identity` and
   `/etc/yubarta/known_hosts`. Store a non-empty API token in the environment file.

```sh
poetry build -f wheel
ansible-playbook -i /secure/inventory.yaml infra/ansible/deploy.yaml --syntax-check
ansible-playbook -i /secure/inventory.yaml infra/ansible/deploy.yaml
```

The playbook installs root-owned target scripts, a command-specific sudo
allowlist, and the control daemon under a dedicated `yubarta` user. The supplied
systemd unit enables **apply mode**. Remove `--apply` from its `ExecStart` to deploy
in dry-run mode. The target user's `adm` group gives read access to Apache logs.
Additional diagnostics that need privilege require explicit sudoers entries.

```sh
systemctl status yubarta
journalctl -u yubarta -f
systemctl stop yubarta
```

### Terraform

This version deploys to existing Linux hosts. `promtV2.md` does not specify a
cloud provider or resources to provision, so this repository has no Terraform
module or applicable Terraform commands. Host provisioning remains with the
operator's existing infrastructure configuration.

## V1 limits

- Run one daemon per database. Incidents execute serially for the single target.
  Database uniqueness and optimistic version checks protect persisted identity
  and transitions; this is not a distributed worker system.
- Backfill is bounded by the configured line count. Identical timestamp-free log
  lines have the same fingerprint and are deduplicated. Use timestamped logs to
  distinguish repeated failures. There are no persistent file offsets.
- After an unclean stop, unfinished incidents and steps are marked failed with
  an interruption reason. An unknown remote command outcome is not retried
  automatically. New observations can create new incidents.
- Stdout and stderr excerpts are capped at 8 KiB each; multiline buffers are
  capped at 64 KiB. Database audit retention is operator-managed.
- The swap script targets a regular Linux swap file on a filesystem that supports
  it. Existing incompatible files are left unchanged and produce a failed step.
