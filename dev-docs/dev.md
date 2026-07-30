# Local dev rig

Everything runs in Docker. There is no supported host-Python workflow: the API, the
tests and Alembic all read `.env`, which points at the `postgres` service by hostname.

## First run

```bash
make init          # build the image, then raise the stack
```

`make init` is `make docker-build` followed by `make up`. The `up` step raises
Postgres first, waits for its healthcheck, runs `alembic upgrade head` as a one-shot
`migrate` service, and only then starts the API. If the migration fails, the API does
not start, which is deliberate: a running API on an unmigrated database fails one
request at a time instead of failing once, loudly, at boot.

Check it is alive:

```bash
curl localhost:8080/api/v1/z/healthz     # {"status":"healthy"}
curl localhost:8080/api/v1/z/whale       # the whale
open http://localhost:8080/docs          # OpenAPI, generated from the routes
```

## Drive the reactive path

```bash
make inject-alarm
```

This runs `dev/inject_alarm.py` inside the api container. It posts a fake Alertmanager
alert whose labels match `java-app-1` in the checked-in `inventory.yaml`, then reads
the incident back **through the API from Postgres** rather than echoing the response,
so a green run is evidence the incident is persisted. It also redelivers the same
alert to show deduplication, and posts an unmatchable alert to show the rejection
path.

What it exercises, end to end:

```
POST /api/v1/webhook/alertmanager
  -> normalize_alertmanager()          Alertmanager JSON to a canonical Signal
  -> match_target_entry()              Signal labels to exactly one inventory target
  -> IncidentStore.create()            one incident per Signal.id, state `received`
  -> GET /api/v1/incidents/{id}        read the persisted incident and its lifecycle log
```

Nothing drives the incident past `received`. The Director (stage 4 of
`dev-docs/roadmap.md`) is what will move it through `diagnosing`, `remediating`,
`verifying` and on to `resolved` or `escalated`, and it does not exist yet. The store
enforces the version guard and the fencing token on every transition regardless, and
those are covered by integration tests.

To see what is in the store without injecting anything:

```bash
make incidents
curl "localhost:8080/api/v1/incidents?limit=5"
curl "localhost:8080/api/v1/incidents?target_name=java-app-1"
```

## Tests

```bash
make test              # whole suite, in the container
make check             # ruff + mypy
```

Integration tests create and drop their own database (`yubarta_test`, from `.env.ci`)
and apply the schema with the project's own Alembic migration, not
`metadata.create_all`. A migration that drifts from the ORM definition therefore fails
the suite instead of surfacing on a deploy. Unit tests never touch Postgres, because
the database fixture is opt-in rather than autouse.

`make test` starts Postgres and runs the migration first (they are the api service's
dependencies), so it works from a cold machine.

## Migrations

```bash
make migrate                            # alembic upgrade head
make migrate-down                       # alembic downgrade -1
make migration MSG="add lease columns"  # autogenerate from ORM changes
make migration-check                    # fail if the ORM has drifted from head
```

While the project is pre-deploy, a schema change is folded into the existing revision
by regenerating it rather than stacked as a new one. That has one trap worth knowing:
**editing a revision in place is invisible to a database that already ran it.** Alembic
sees the same revision id at head and does nothing, so the dev database keeps the old
columns while the test suite passes, because integration tests build their database
from scratch on every run. If a query fails on a column you can see in `orm.py`, that
is what happened:

```bash
make migrate-down && make migrate      # or `make clean && make up` to start over
make migration-check                   # confirms the ORM and head agree
```

Migrations are never applied from the application's startup path. `Database` builds an
engine and nothing else. The reason is replica count: the API is meant to run as more
than one process, and several of them racing to migrate the same database on boot is a
worse failure than a deploy step that has to be ordered.

## Database

```bash
make psql                              # psql on the dev database
make logs CONTAINER=api                # follow one service
make logs                              # follow everything
```

Dev Postgres is published on host port **5433** (not 5432) to stay out of the way of a
local install. Inside the compose network it is `postgres:5432`, which is what `.env`
uses.

To inspect the schema by hand:

```sql
\d incidents
select id, state, version, lease_generation, target_name from incidents order by created_at desc limit 5;
select from_state, to_state, occurred_at from incident_transitions order by occurred_at;
select remediation_name, idempotency_key, approval_status, outcome from remediation_attempts;
```

## Teardown

```bash
make down          # stop containers, keep the data
make clean         # stop containers and delete volumes (drops the dev database)
```

## What the rig does not have yet

- **No fake Prometheus.** Alerts are injected by posting the Alertmanager payload
  directly. A real Prometheus plus Alertmanager pair only adds value once
  `proactive-scanner` (stage 6) needs to be observed reacting to real rule
  evaluation.
- **Kafka and Redis run but nothing uses them.** They are in the compose file for the
  Director and scanner stages. The API deliberately does not depend on their
  healthchecks, so they never gate a test run or a `compose run`.
- **No SOPS or age setup.** `inventory.yaml` carries `sops://` credential references
  as opaque strings and nothing resolves them yet (stage 5).
