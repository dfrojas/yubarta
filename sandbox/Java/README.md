# Manual Java lab: real Tomcat

This independent manual lab runs Tomcat 10.1.55 on Java 17, a servlet packaged
as `ROOT.war`, SSH, and PostgreSQL. Yubarta runs on your host. Automated tests
use their own minimal Java workload in `tests/e2e/scenarios/java/`.

Tomcat runs as the `tomcat` user. SSH user `yubarta` can use passwordless sudo
only for `tomcat-control status`, `tomcat-control restart`, and reading the last
60 lines of `catalina.out`. The control script calls
Tomcat's real `catalina.sh`; it does not replace Tomcat with a simulated service.
The container remains alive after a JVM crash, allowing SSH remediation.

## 1. Install and start

Requires Python 3.12+, Poetry 2.x, and Docker Compose v2 with a running engine.
Run all commands from the repository root. Java and PostgreSQL are installed
inside the images. Poetry manages the Python environment automatically; use
`poetry run` to execute Yubarta without manually creating or activating an environment.

```sh
poetry env use python3.12
poetry install
. sandbox/Java/local.env
docker compose -f sandbox/Java/docker-compose.yaml up -d --build --wait --wait-timeout 120
curl --fail "http://127.0.0.1:${YUBARTA_JAVA_HTTP_PORT}/"
curl --fail "http://127.0.0.1:${YUBARTA_JAVA_HTTP_PORT}/health"
poetry run yubarta serve --config sandbox/Java/config.yaml --apply
```

The root endpoint identifies Apache Tomcat and the JVM PID. `/health` returns
`OK` from the deployed servlet. The runtime creates tables in the fresh database.

Default connections:

| Service | Address |
| --- | --- |
| Tomcat application | `http://127.0.0.1:18080` |
| SSH | `127.0.0.1:2222`, user/password `yubarta` |
| PostgreSQL | `127.0.0.1:5433`, database/user/password `yubarta` |
| Control API | `http://127.0.0.1:8787` |

If a port is occupied, export the corresponding `YUBARTA_JAVA_*_PORT` before
sourcing `local.env`. Use the same values in every terminal. The config loader
does not load env files automatically; sourcing exports the values for both
Compose and Yubarta. This YAML is specific to this lab, not `config.example.yaml`.

## 2. Observe and inject a failure

In another terminal:

```sh
. sandbox/Java/local.env
poetry run yubarta status
poetry run yubarta scanners
curl --fail "http://127.0.0.1:${YUBARTA_JAVA_HTTP_PORT}/"
docker compose -f sandbox/Java/docker-compose.yaml exec tomcat tomcat-control crash
poetry run yubarta incidents
```

Wait for the command scanner to report `connected: true` before injecting the
fault. `crash` sends SIGKILL to the real Tomcat JVM. It does not simulate a real
OOM. It leaves SSH and PostgreSQL available. The scanner checks every three
seconds; Yubarta then collects diagnostics and restarts Tomcat.

Use the ID from `poetry run yubarta incidents`:

```sh
poetry run yubarta incident <incident-id>
curl --fail "http://127.0.0.1:${YUBARTA_JAVA_HTTP_PORT}/health"
curl --fail "http://127.0.0.1:${YUBARTA_JAVA_HTTP_PORT}/"
```

Expected: incident `RESOLVED`, successful `restart-tomcat` remediation, HTTP
`OK`, and a different JVM PID. Recovery can be fast enough that a subsequent
manual curl never sees the outage; the incident records the failed checks.

For a graceful stop instead:

```sh
docker compose -f sandbox/Java/docker-compose.yaml exec tomcat tomcat-control stop
```

Do not use `docker compose stop tomcat` for this exercise: that also removes SSH,
so Yubarta cannot restart the JVM inside the stopped container.

## 3. Dry-run

Stop Yubarta with Ctrl-C, ensure Tomcat is running, and restart Yubarta without
`--apply`:

```sh
docker compose -f sandbox/Java/docker-compose.yaml exec tomcat tomcat-control restart
poetry run yubarta serve --config sandbox/Java/config.yaml
```

Inject the same crash from another terminal. Diagnostics and checks run, but
remediation is recorded as `SKIPPED`, and the incident ends as `FAILED` with a
dry-run reason. Tomcat stays down. The periodic scanner can create more incidents
while it remains down; restore it after inspection:

```sh
docker compose -f sandbox/Java/docker-compose.yaml exec tomcat tomcat-control restart
```

## 4. Troubleshoot and reset

```sh
poetry run yubarta scanners
docker compose -f sandbox/Java/docker-compose.yaml ps
docker compose -f sandbox/Java/docker-compose.yaml logs --tail 100
docker compose -f sandbox/Java/docker-compose.yaml exec tomcat \
  tail -n 100 /usr/local/tomcat/logs/catalina.out
```

Stop Yubarta with Ctrl-C before stopping its dependencies:

```sh
# Keep incident history in the named PostgreSQL volume.
docker compose -f sandbox/Java/docker-compose.yaml down

# Full reset: also delete this lab's incident database.
docker compose -f sandbox/Java/docker-compose.yaml down -v
```

This scenario exercises real Tomcat and servlet recovery using a command watch.
It has no Apache proxy, AJP connector, swap provisioning, or systemd. Those
behaviors are not part of this manual scenario. Nothing auto-restarts Tomcat:
recovery must come from Yubarta or an explicit user command.
