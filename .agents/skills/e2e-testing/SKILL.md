---
name: e2e-testing
description: Design, change, and debug Yubarta end-to-end tests in tests/e2e, including Docker scenarios, process fixtures, polling, isolation, and failure diagnostics. Use when adding or reviewing automated E2E coverage.
---

# Yubarta E2E testing

Adapted from Kubernetes [Writing good e2e tests](https://github.com/kubernetes/community/blob/main/contributors/devel/sig-testing/writing-good-e2e-tests.md).
Use its reliability, debugging, cleanup, isolation, and resource principles with
pytest and asyncio. Do not introduce Ginkgo or Kubernetes as dependencies.

## Define the boundary

- State the user-visible behavior in the test name and docstring.
- Product E2E tests start the installed `yubarta serve` command with YAML and
  inspect the Control API/CLI and the actual target application.
- Do not assemble `IncidentService`, call lifecycle methods, or query the ORM
  to assert product E2E results. Those tests belong in `tests/integration/`.
- Python-generated test data is valid. YAML is covered here because it is the
  product's configuration interface, not because all E2E tests require YAML.
- Use real SSH and PostgreSQL for the recovery scenario. Reuse the isolated
  `test_db` fixture; do not connect to a manual or production database.
- Automated workloads live under `tests/e2e/scenarios/<scenario>/`. Keep them
  small and fast. The minimal Java HTTP service is intentional; it does not
  claim coverage of Tomcat, Apache, AJP, systemd, or a real out-of-memory event.
- Manual product labs live under `sandbox/<scenario>/`, independently of tests.
  Never start, stop, or reset a user's manual lab from an automated test.
- Synthetic log input is allowed when log ingestion is the subject. Label it
  explicitly; never describe a test-written AJP line as an Apache-generated error.

## Fixtures and resources

- Prefer typed pytest fixtures for shared setup. Keep lifecycle setup in
  `conftest.py` and reusable waits/process helpers in focused helper modules.
- Build the target image once per test session. Use unique image/container names,
  OS-assigned loopback ports, temporary files, and a database per test.
- Register cleanup immediately after acquiring each resource, including during
  partial startup. Release in reverse order using context managers or `finally`.
- Bound subprocess commands and teardown. Terminate the product gracefully,
  then kill it if the deadline expires. Report an unexpected forced shutdown.
- Let cancellation propagate. Cleanup must also work on test failure and Ctrl-C.
- Keep only the resources needed for the behavior under test. Do not add a full
  Tomcat stack to the fast Java scenario.

## Conditions, deadlines, and speed

- Poll an observable condition instead of sleeping for an assumed startup time.
- Use shared timeout defaults and monotonic deadlines. Bound each SSH/HTTP/Docker
  operation as well as the whole wait; retries must not extend the total deadline.
- Retain both the last observed value and the last transient error. A timeout
  must name the resource, expected condition, elapsed limit, and those details.
- Retry expected transport/readiness failures only. Abort early on process exit,
  a terminal failed incident, malformed data, or another unrecoverable condition.
- Aim for under two minutes per scenario, including failure paths after the
  image is built. Cold image downloads/builds have separate bounded setup limits.
- Do not rerun failed tests until green or suppress real failures with skips.
  Report missing required Docker/PostgreSQL dependencies clearly.
- For a claim that something remains unchanged, observe it for a bounded window;
  one immediate sample does not establish that it stays unchanged.

## Assertions and diagnostics

- Assert outcomes: incident state, recorded remediation, application response,
  and a new process after recovery. Do not couple tests to incidental log wording,
  UUID values, transition counts, or exact timing.
- Verify the application is healthy before injecting a fault. Ensure recovery is
  attributable to Yubarta: the workload must not auto-restart independently.
- Capture product output to a file rather than an unread pipe that can block.
- On failure, attach product logs, relevant API state, container state, and target
  logs before cleanup. Keep successful runs quiet. Do not log secret environment
  values or full container inspection data containing credentials.
- Preserve useful assertion values rather than reducing them to booleans.
- Fault injection may use Docker exec/SSH against resources owned by the test.
  Never disrupt unrelated containers or rely on global counts of resources.

## Verification workflow

1. Read the existing fixtures and scenario before adding new helpers.
2. Identify the boundary, expected outcome, resource ownership, and failure path.
3. Implement the smallest scenario with bounded waits and cleanup.
4. Run the affected tests with `python -m pytest tests/e2e -q` and run relevant
   integration/unit tests when their shared fixtures or application code change.
5. Check that resources are removed and failures include actionable diagnostics.
6. Document dependencies, execution commands, coverage, and synthetic inputs in
   `tests/e2e/README.md`. Explain any justified slow or disruptive scenario.
