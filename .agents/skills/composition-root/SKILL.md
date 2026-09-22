---
name: composition-root
description: How Yubarta builds its objects and controls their life. Use when you add a service, connect dependencies, own a resource such as the database or the scanners, or change the runtime and its life cycle. Covers dependency injection by hand, without a library.
---

# Composition root

This skill tells you how Yubarta builds its objects and controls their life. This is an application design rule. It is not a web rule. The API is one entrypoint only.

The composition root is the one place that builds all objects. In Yubarta, this place is `yubarta/runtime.py` (`YubartaRuntime`). Refer to the ADR `docs/records/adr/0001-runtime-service-composition.md`.

## Terms

- **Composition root**: the one place that builds objects and connects them. Do not put this work in many modules.
- **Service**: an object that does domain work. For example, `IncidentService`. A service gets its helpers (config, sessions, rules) in its constructor. A service gives behavior. It does not give data.
- **Runtime**: the object that owns the process resources and the services. Do not use it for business logic. Do not use it as a list of names.

## Rules

- **One owner for each resource.** The runtime makes and closes the engine, the session factory, and the scanner supervisor. No other code opens them.
- **Give each service its dependencies.** Put the dependencies in the constructor. A service must not use a global, a module singleton, or a session that it makes itself.
- **Put the services in one typed group.** Use a dataclass. Give each service one field. Keep the dataclass private. Give access with one property:

  ```python
  @dataclass
  class RuntimeServices:
      incidents: IncidentService
      # diagnosis: DiagnosisService   # add field, wire in _build_services

  @property
  def services(self) -> RuntimeServices:
      if self._services is None:
          raise RuntimeError("Runtime not set up")
      return self._services
  ```

- **Use one access path.** Give access to the group or to each service. Do not do both.
- **Keep each change small.** To add a service, add one field to the group and one line to the build method. Do not add public runtime API, a helper method, or a special condition in `setup()`.
- **Build in one place.** `setup()` builds the infrastructure first. Then it calls one method that builds the service group.
- **Connect services at the root.** Do not connect a service to another service inside a service.
- **Stop with an error before setup.** The property raises an error. It does not return `None`. Then the call sites do not need `None` checks.

## Do not do

- Do not use a dependency injection library. The object graph is small. A library adds extra steps and does not remove real work.
- Do not use a list with string keys (`services.get("incidents")`). The computer cannot check the types. You cannot go to the code of a service.
- Do not add one behavior method for each service to the runtime. Then the runtime becomes too large.
- Do not use module globals or singletons for resources.

## Life cycle

- The runtime has `setup()`, `shutdown()`, and a `lifespan()` context manager. The FastAPI lifespan uses that context manager. Do not write the same steps again in the app factory.
- Startup starts long tasks only. It does not wait for them to finish. If it waits, the server cannot start.
- `shutdown()` stops the tasks and closes the resources. It closes them in the opposite order of startup.

## Tests

- A test makes a runtime with a test database. The test calls `setup()`. Then the test gives the runtime to the app factory. The test needs no server and no global reset.
- The app factory accepts a runtime that you already built. Then the test controls the life of the runtime.

## Alternative

If the service group becomes too large, or if the services become dependent on each other, use one group for each capability. Before you do this, write a new ADR.
