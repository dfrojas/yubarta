# 1. Runtime service composition

Date: 2026-09-18

## Status

Accepted

## Context

`YubartaRuntime` is the composition root of the process. It owns the database engine, the session factory, the scanner supervisor, and the services. Before this decision, it had one service only: `IncidentService`. The runtime kept this service in `_service` and gave access with a `service` property. `setup()` built the service at the same time as the infrastructure.

This shape worked with one service. But it does not scale. Each new service needs a new field, a new property, special code in `setup()`, and possibly one behavior method on the runtime. Then the runtime becomes one large object with two tasks: own the resources and hold the services. Also, the name `service` has no meaning when there are many services.

Rejected alternatives:

* A generic list with string keys (`services.get("incidents")`). The computer cannot check the types. You cannot go to the code of a service. This gives no benefit at this size.
* A dependency injection library. The object graph is small. The objects are connected by hand. The life of the graph must stay with the FastAPI lifespan. A library adds extra steps and does not remove real work.
* Access to the service group and to each service. This is two access paths to the same object. The extra property must stay for all time.
* Build the services in the API entrypoint. This puts "build the graph" and "run the process" in different places. But then each test that needs a runtime must build more objects.

## Decision

`YubartaRuntime` stays the composition root. All services are in one typed group: a `RuntimeServices` dataclass with one field for each service:

```python
@dataclass
class RuntimeServices:
    incidents: IncidentService
    # diagnosis: DiagnosisService   # add field, wire in _build_services
```

The runtime keeps the group and gives access with one property, `services`. This property raises `RuntimeError` if the runtime is not set up. There are no properties for single services and no string list. `setup()` builds the infrastructure. Then it calls `_build_services()`. This method builds the service group. It is the only place that builds the group. Inside the runtime, the call sites use `runtime.services.incidents`.

To add a service, add one field and one construction line. The public API of the runtime does not change. The `composition-root` skill contains the same rule.

## Consequences

Easier:

* To add a service, you do not add properties, helper methods, or public API.
* One typed access path lets the computer check the types and lets you go to the code.
* All construction is in one place. A future `shutdown()` can close all services in one place.
* The dead `service` property and the `if self._service is None` checks are gone.

Harder or more risky:

* `RuntimeServices` is wider than one `service`. The runtime now names each service type. The group becomes larger when the number of services becomes larger. This is satisfactory for a small, fixed set.
* If the number of services increases, or if the services become dependent on each other, the group becomes one large object. The alternative is one group for each capability. In that design, each capability connects its own service.
* `_build_services()` is synchronous. If a service needs an async setup, this method must become async.

Mitigations in place:

* Keep the services independent. Connect a service to another service in `_build_services()` only. This is the only construction point.
* If one group for each capability is necessary, write a new ADR.
