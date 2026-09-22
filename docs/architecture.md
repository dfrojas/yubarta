# Code structure

The decision is recorded in [ADR 2](records/adr/0002-core-controllers-and-drivers.md).
The package names follow commit `b6e8f54000be4cca4d5ed039d2d6515cbc58e709`.

```text
yubarta/
  main.py                         executable entry
  runtime.py                      construction, startup, shutdown
  core/
    models.py                     incidents, observations, operation results
    enums.py                      incident and step states
    interfaces.py                 repository and command ports
    errors.py
    state_machine.py
    rules.py
  controllers/
    incidents.py                  incident lifecycle and queries
    diagnostics.py                evidence collection
    checks.py                     prechecks and verification
    unit_of_work.py                transaction contract
    remediations/
      runner.py                   execution and dry-run policy
      scripts/
    scanners/
      contracts.py                lifecycle, source ports, immutable status
      base.py                     task ownership and retry support
      supervisor.py               start/stop the scanner set
      remote_file.py
      remote_command.py
      parsing/
  drivers/
    config/
      config_schemas.py           YAML input models
      loader.py                   load, expand, validate, normalize
    db/
      initialization.py
      sessions.py
      orm.py
      repository.py               rows to domain models
      sqlalchemy.py               SQLAlchemy Unit of Work
    network/
      ssh.py
      files.py
      http.py
  entrypoints/
    api_server/
      app.py
      dependencies.py
      security.py
      schemas.py
      health.py
      v1/
        router.py
        routes/
    cli/
      launcher.py
      commands.py
  config/
    settings.py                   normalized application configuration
```

## Follow an observation

1. `main.py` loads the Typer application. `serve` loads YAML and builds the API.
2. The API lifespan enters `YubartaRuntime.lifespan()`.
3. Runtime builds the drivers, controllers, and scanner supervisor. It connects
   the scanners to the incident service through a callback.
4. A scanner obtains command results or log lines through an injected source.
   It normalizes observations and delivers them to the callback.
5. The incident service evaluates rules, records the trigger, and coordinates
   diagnostics, prechecks, remediations, and verification.
6. Each persistence operation uses its own UoW. External commands and HTTP checks
   run outside the database transaction.
7. API routes obtain incident results from the service. They convert them to the
   public response schemas. The CLI reads that API.

The supervisor manages scanner tasks, not incident workers. This version uses
direct in-process delivery. File sources own their SSH tail processes; cancellation
closes the source before the scanner finishes stopping.

## Configuration

`config.example.yaml` is the product input example. Runtime code receives
`AppConfig` from `config/settings.py`, not raw YAML dictionaries.

The complete input model is `ConfigInput` in
`drivers/config/config_schemas.py`. It can also produce a JSON Schema with
`ConfigInput.model_json_schema()`.

Command watches support:

```yaml
watch:
  - command:
      run: systemctl is-active example
      interval: 30s
      expect:
        exit_code: 0
```

Watch expectations describe a trigger; check expectations describe health.
Durations accept numbers in seconds and strings ending in `ms`, `s`, or `m`.
Unknown keys are rejected, including nested keys. At least one watch and one
health check are required. Error messages include the file.

## Development checks

```sh
poetry install
poetry check
poetry run ruff check .
poetry run ruff format --check .
poetry run pytest -q
```

Integration and E2E tests start isolated PostgreSQL and SSH sandbox containers
through Docker Compose. See [the test guide](../README.md#tests) for the recovery,
reconnection, and graceful shutdown scenarios.
