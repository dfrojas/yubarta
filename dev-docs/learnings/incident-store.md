# Learning Note: incident-store

## Three mechanisms, three races, and why merging any two removes a guarantee

The store carries an optimistic `version`, a `lease_generation` fencing token, and a
pre-execution idempotency key. They look redundant until you name what each one
detects:

| Race | Mechanism | What it sees |
|---|---|---|
| Lost update | `version` | the state moved between a caller's read and its write |
| Stale owner | `lease_generation` | ownership moved, which a correct `version` cannot reveal |
| Duplicate external effect | idempotency key | an SSH command or API call already ran |

The temptation to collapse `version` and `lease_generation` into one counter is strong,
and it is wrong in a way no test catches unless the case is written deliberately. A
replica whose lease expired can hold a perfectly correct `expected_version`, because
nobody has written yet, and still have no right to act. So the one test that keeps the
design honest is: **a stale lease generation is rejected even when the expected version
matches.** Without it, someone merges the two columns during a refactor, every test
still passes, and one guarantee is gone.

The third mechanism is not database-level at all. `version` and the fencing token
protect a row; neither can un-send an SSH command. Only recording the attempt before
executing it, under a unique constraint, can prevent a remediation from running twice.

## Optimistic control is not a performance choice here

The design originally specified `SELECT ... FOR UPDATE` and explicitly rejected a
version column. Reversing that was the largest decision of the stage (ADR-0006), and
the reason has nothing to do with throughput.

Pessimistic locking makes a second writer **wait and then succeed**. For a state
machine driven by a possibly-stale replica, succeeding is precisely the bug: the loser's
decision was computed from state it read before the winner's write, and blocking does
not recompute it, it just delays applying it. A rejected write is not lock contention to
smooth over, it is evidence that the caller's view is stale and its decision has to be
made again. Optimistic control surfaces that; pessimistic locking hides it.

The visible consequence is that callers cannot blindly retry. That is intended, and it
is why the errors are distinguishable types rather than one generic failure.

## Reading `from_state` without a lock is still correct

The transition log needs the state the incident is leaving. The obvious move after
dropping `FOR UPDATE` is to worry that a plain `SELECT` for `from_state` is racy.

It is not, and the argument is worth writing down because it is the kind of thing that
gets "fixed" back into a lock later. The read happens inside the same transaction as the
conditional update. If any writer committed in between, it would have incremented
`version`, and then the update's `WHERE version = :expected_version` matches zero rows
and the whole transition is rejected. So `from_state` is only ever used on the path where
no concurrent write happened. The guard does the work; the read is informational.

## Why a Unit of Work appeared at this stage and not earlier

Nothing in the project needed a transaction boundary before, because there was no real
schema. This store's central claim, that the denormalized `incidents.state` can never
drift from the append-only log, rests entirely on a conditional `UPDATE` and an `INSERT`
landing together. Left implicit, that boundary belongs to whoever happens to hold the
session, which is not a decision anyone made.

Two alternatives were rejected. Per-method commits break the atomicity outright, and
nothing in the code would say it was ever intended. Caller-supplied sessions work, but
push SQLAlchemy into the Director, which is exactly what the domain port exists to
prevent. Naming the boundary makes "what commits together" something the store owns and
states (ADR-0007).

The rule that falls out of it: external effects never run inside a unit of work. They
cannot enlist in a Postgres transaction and a rollback cannot undo them, so the attempt
row commits *before* the effect and the outcome commits *after*. A crash between the two
is then detectable rather than silent.

## Discoveries while implementing

**The append-only log had no reader.** Every method to write transitions existed, none to
read them. The design says the last transition is ground truth for crash recovery and
that folding the history must agree with the current state, and neither claim was
reachable through the port. A write-only audit log is a table that costs storage and
proves nothing. `list_transitions` was added, and the detail route returns the log
alongside the incident, because "where is it now" and "how did it get here" are rarely
useful separately.

**The completed-key branch is nearly unreachable, and that is a property of the key
derivation.** The attempt sequence is derived from the count of *completed* attempts plus
one, so an in-flight attempt keeps its key until it finishes. That is what makes
crash-and-retry collide instead of re-executing. The side effect is that once an attempt
completes, a fresh `record_attempt` computes the *next* sequence, so it can never collide
with the completed one through normal use. The only path to that collision is a genuine
race: two replicas derive sequence 1, one inserts and completes, the other inserts late
and the unique constraint rejects it. Testing it meant reproducing the interleaving, not
the result, so the test patches only the moment the winner completes and lets the real
constraint do the rejecting.

**Editing a migration in place is invisible to a database that already ran it.** Folding
the concurrency columns into the single existing revision is correct pre-deploy, but
Alembic sees the same revision id at head and does nothing. The suite stayed green
because integration tests build their database from scratch every run, while the dev
database silently kept the old schema, and the first end-to-end run failed on
`column "version" does not exist`. The test suite was structurally incapable of catching
it. That is a good argument for having the tests apply the real migration rather than
`metadata.create_all`, which is now how they work.

## The one that generalizes: green tests, red CI, and an app that could not boot

This is the finding worth keeping. Before this change the project had three archived
stages, a passing local impression, and:

- `uvicorn yubarta.main:app` died on `ImportError`. A previous stage removed the
  `SignalStore` port while the webhook route still imported it.
- `pytest` collected **zero** tests. `conftest.py` imported a function that no longer
  existed, and one broken import in a shared conftest fails every test in the tree,
  including tests that have nothing to do with it.
- `docker compose build` failed. The compose file built a Rust service whose sources had
  been deleted two stages earlier.
- `ruff` reported 11 errors and `mypy` could not resolve modules, so CI was red.

Each individually is a small oversight. Together they mean nothing had actually run in a
long time, and the reason they accumulated is structural: the work was organized
capability by capability, each with its own port, implementation and isolated tests, and
nothing forced the capabilities to be connected. The inventory matcher had tests and no
caller. The incident store was fully written and instantiated nowhere.

Passing tests do not tell you the system runs. They tell you the parts you tested behave.
The check that catches this is a driver script that exercises the real path against the
raised stack (`make inject-alarm`), run as part of finishing a stage rather than after
the fact. It is the only step in this stage that would have failed on day one of the
previous three.
