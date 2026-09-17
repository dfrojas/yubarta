from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import update

from yubarta.domain.signal import Signal, SignalSource, SignalStatus
from yubarta.incident.errors import (
    AttemptNotFoundError,
    ConcurrentModificationError,
    DuplicateAttemptError,
    IncidentNotFoundError,
    StaleLeaseError,
)
from yubarta.incident.models import AttemptApproval, AttemptOutcome, IncidentState
from yubarta.infra.db.orm import incidents
from yubarta.infra.db.repository import SqlAlchemyIncidentStore

pytestmark = pytest.mark.integration

BASE_TIME = datetime(2026, 7, 30, 12, 0, 0, tzinfo=timezone.utc)
LIFECYCLE = [
    IncidentState.diagnosing,
    IncidentState.remediating,
    IncidentState.verifying,
    IncidentState.resolved,
]


def make_signal(minutes_offset: int = 0, labels: dict[str, str] | None = None) -> Signal:
    """A distinct signal per offset: `Signal.id` folds in `fired_at`, so a different
    offset is a different incident and the same offset twice is a redelivery.
    """
    return Signal(
        status=SignalStatus.firing,
        source=SignalSource.webhook,
        labels=labels or {"service": "java-app", "role": "api"},
        fired_at=BASE_TIME + timedelta(minutes=minutes_offset),
        raw={"alertname": "DiskFull"},
    )


async def walk_to(incident_store, incident, *states):
    for state in states:
        incident = await incident_store.transition(
            incident.id,
            state,
            expected_version=incident.version,
            lease_generation=incident.lease_generation,
        )
    return incident


async def promote_lease(unit_of_work, incident_id: str, generation: int) -> None:
    """Stand in for the Director acquiring a lease, which does not exist yet.

    Nothing in the codebase increments `lease_generation` until stage 4, so the
    fencing token can only be exercised by writing a newer generation directly.
    """
    async with unit_of_work.begin() as session:
        await session.execute(
            update(incidents)
            .where(incidents.c.id == incident_id)
            .values(lease_generation=generation, lease_owner="director-1")
        )


async def test_create_persists_a_received_incident(incident_store):
    signal = make_signal()

    incident = await incident_store.create(signal, "java-app-1")

    assert incident.state == IncidentState.received
    assert incident.target_name == "java-app-1"
    assert incident.signal.id == signal.id
    assert incident.version == 0
    assert incident.lease_generation == 0
    assert incident.lease_owner is None
    assert incident.attempts == []


async def test_create_is_readable_back_by_id(incident_store):
    created = await incident_store.create(make_signal(), "java-app-1")

    read_back = await incident_store.get(created.id)

    assert read_back is not None
    assert read_back.id == created.id
    assert read_back.signal.labels == created.signal.labels


async def test_create_dedupes_on_signal_id(incident_store):
    signal = make_signal()

    first = await incident_store.create(signal, "java-app-1")
    second = await incident_store.create(signal, "java-app-1")

    assert second.id == first.id
    assert len(await incident_store.list_recent(10)) == 1


async def test_get_returns_none_for_unknown_incident(incident_store):
    assert await incident_store.get("does-not-exist") is None


async def test_full_lifecycle_persists_and_reads_back(incident_store):
    incident = await incident_store.create(make_signal(), "java-app-1")

    resolved = await walk_to(incident_store, incident, *LIFECYCLE)

    assert resolved.state == IncidentState.resolved
    read_back = await incident_store.get(incident.id)
    assert read_back.state == IncidentState.resolved


async def test_transition_history_folds_back_to_current_state(incident_store):
    incident = await incident_store.create(make_signal(), "java-app-1")
    final = await walk_to(incident_store, incident, *LIFECYCLE)

    transitions = await incident_store.list_transitions(incident.id)

    assert [transition.to_state for transition in transitions] == LIFECYCLE
    assert transitions[0].from_state == IncidentState.received
    # Folding the append-only log means taking the last destination, and it has to
    # agree with the denormalized column written in the same transaction.
    assert transitions[-1].to_state == final.state


async def test_each_successful_transition_increments_version(incident_store):
    incident = await incident_store.create(make_signal(), "java-app-1")

    observed_versions = []
    for state in LIFECYCLE:
        incident = await incident_store.transition(
            incident.id,
            state,
            expected_version=incident.version,
            lease_generation=incident.lease_generation,
        )
        observed_versions.append(incident.version)

    assert observed_versions == [1, 2, 3, 4]


async def test_stale_expected_version_is_rejected_and_changes_nothing(incident_store):
    incident = await incident_store.create(make_signal(), "java-app-1")
    stale_version = incident.version
    winner = await incident_store.transition(
        incident.id,
        IncidentState.diagnosing,
        expected_version=stale_version,
        lease_generation=0,
    )

    with pytest.raises(ConcurrentModificationError) as rejection:
        await incident_store.transition(
            incident.id,
            IncidentState.escalated,
            expected_version=stale_version,
            lease_generation=0,
        )

    assert rejection.value.expected_version == stale_version
    assert rejection.value.persisted_version == winner.version
    unchanged = await incident_store.get(incident.id)
    assert unchanged.state == IncidentState.diagnosing
    assert unchanged.version == winner.version
    # The rejected transition left no trace in the append-only log either.
    assert len(await incident_store.list_transitions(incident.id)) == 1


async def test_transition_on_unknown_incident_raises_not_found(incident_store):
    with pytest.raises(IncidentNotFoundError):
        await incident_store.transition(
            "does-not-exist",
            IncidentState.diagnosing,
            expected_version=0,
            lease_generation=0,
        )


async def test_stale_lease_is_rejected_even_when_version_matches(incident_store, unit_of_work):
    """The case that keeps the two guards from collapsing into one mechanism.

    The expected version is correct here, so the version guard alone would let this
    write through. Only the fencing token can tell that the caller no longer owns the
    incident.
    """
    incident = await incident_store.create(make_signal(), "java-app-1")
    await promote_lease(unit_of_work, incident.id, generation=3)

    with pytest.raises(StaleLeaseError) as rejection:
        await incident_store.transition(
            incident.id,
            IncidentState.diagnosing,
            expected_version=incident.version,
            lease_generation=incident.lease_generation,
        )

    assert rejection.value.submitted_generation == 0
    assert rejection.value.persisted_generation == 3
    untouched = await incident_store.get(incident.id)
    assert untouched.state == IncidentState.received
    assert untouched.version == 0
    assert await incident_store.list_transitions(incident.id) == []


async def test_current_lease_generation_is_accepted(incident_store, unit_of_work):
    incident = await incident_store.create(make_signal(), "java-app-1")
    await promote_lease(unit_of_work, incident.id, generation=3)

    transitioned = await incident_store.transition(
        incident.id,
        IncidentState.diagnosing,
        expected_version=incident.version,
        lease_generation=3,
    )

    assert transitioned.state == IncidentState.diagnosing
    assert transitioned.lease_generation == 3


async def test_attempt_is_recorded_before_completion(incident_store):
    incident = await incident_store.create(make_signal(), "java-app-1")

    attempt = await incident_store.record_attempt(incident.id, "restart-java-app")

    assert attempt.outcome is None
    assert attempt.completed_at is None
    assert attempt.approval_status == AttemptApproval.not_required
    assert attempt.idempotency_key == f"{incident.id}:restart-java-app:1"
    read_back = await incident_store.get(incident.id)
    assert [recorded.id for recorded in read_back.attempts] == [attempt.id]


async def test_completing_an_attempt_records_outcome_and_timestamp(incident_store):
    incident = await incident_store.create(make_signal(), "java-app-1")
    attempt = await incident_store.record_attempt(incident.id, "restart-java-app")

    completed = await incident_store.complete_attempt(
        attempt.id,
        AttemptOutcome.succeeded,
        {"exit_code": 0},
    )

    assert completed.outcome == AttemptOutcome.succeeded
    assert completed.completed_at is not None
    assert completed.evidence == {"exit_code": 0}


async def test_repeated_key_rejects_an_in_flight_attempt(incident_store):
    incident = await incident_store.create(make_signal(), "java-app-1")
    first = await incident_store.record_attempt(incident.id, "restart-java-app")

    with pytest.raises(DuplicateAttemptError) as rejection:
        await incident_store.record_attempt(incident.id, "restart-java-app")

    assert rejection.value.existing_attempt.id == first.id
    assert rejection.value.existing_attempt.outcome is None


async def test_second_attempt_after_completion_gets_the_next_sequence(incident_store):
    incident = await incident_store.create(make_signal(), "java-app-1")
    first = await incident_store.record_attempt(incident.id, "restart-java-app")
    await incident_store.complete_attempt(first.id, AttemptOutcome.failed, None)

    second = await incident_store.record_attempt(incident.id, "restart-java-app")

    assert second.attempt_sequence == 2
    assert second.idempotency_key == f"{incident.id}:restart-java-app:2"


async def test_duplicate_key_race_surfaces_the_completed_winner(incident_store, monkeypatch):
    """Two writers derive the same key, and the winner finishes mid-flight.

    The patched lookup reproduces the interleaving rather than the result: this caller
    derived sequence 1 while nothing was completed, the winner completed before the
    insert landed, so the unique constraint is what rejects the write. The integrity
    error must not escape, and the error must carry the winner's recorded outcome so
    the caller reads the result instead of re-running the remediation.
    """
    incident = await incident_store.create(make_signal(), "java-app-1")
    winner = await incident_store.record_attempt(incident.id, "restart-java-app")

    async def complete_the_winner_then_miss(self, session, idempotency_key):
        monkeypatch.undo()
        await incident_store.complete_attempt(winner.id, AttemptOutcome.failed, {"exit_code": 1})
        return None

    monkeypatch.setattr(SqlAlchemyIncidentStore, "_read_attempt_by_key", complete_the_winner_then_miss)

    with pytest.raises(DuplicateAttemptError) as rejection:
        await incident_store.record_attempt(incident.id, "restart-java-app")

    assert rejection.value.existing_attempt.id == winner.id
    assert rejection.value.existing_attempt.outcome == AttemptOutcome.failed


async def test_attempt_on_unknown_incident_raises_not_found(incident_store):
    with pytest.raises(IncidentNotFoundError):
        await incident_store.record_attempt("does-not-exist", "restart-java-app")


async def test_pending_approval_resolves_to_approved(incident_store):
    incident = await incident_store.create(make_signal(), "java-app-1")
    attempt = await incident_store.record_attempt(
        incident.id,
        "restart-java-app",
        approval_status=AttemptApproval.pending,
    )
    assert attempt.approval_status == AttemptApproval.pending

    approved = await incident_store.resolve_approval(attempt.id, AttemptApproval.approved, "diego")

    assert approved.approval_status == AttemptApproval.approved
    assert approved.approved_by == "diego"
    assert approved.approved_at is not None


async def test_pending_approval_resolves_to_denied(incident_store):
    incident = await incident_store.create(make_signal(), "java-app-1")
    attempt = await incident_store.record_attempt(
        incident.id,
        "restart-java-app",
        approval_status=AttemptApproval.pending,
    )

    denied = await incident_store.resolve_approval(attempt.id, AttemptApproval.denied, "diego")

    assert denied.approval_status == AttemptApproval.denied
    assert denied.approved_by == "diego"


async def test_non_approval_attempt_stays_not_required(incident_store):
    incident = await incident_store.create(make_signal(), "java-app-1")
    attempt = await incident_store.record_attempt(incident.id, "rotate-and-flush-logs")

    completed = await incident_store.complete_attempt(attempt.id, AttemptOutcome.succeeded, None)

    assert completed.approval_status == AttemptApproval.not_required
    assert completed.approved_by is None
    assert completed.approved_at is None


async def test_resolving_an_unknown_attempt_raises_not_found(incident_store):
    with pytest.raises(AttemptNotFoundError):
        await incident_store.resolve_approval("does-not-exist", AttemptApproval.approved, "diego")


async def test_completing_an_unknown_attempt_raises_not_found(incident_store):
    with pytest.raises(AttemptNotFoundError):
        await incident_store.complete_attempt("does-not-exist", AttemptOutcome.succeeded, None)


async def test_list_by_target_returns_only_that_target_most_recent_first(incident_store):
    older = await incident_store.create(make_signal(0), "java-app-1")
    newer = await incident_store.create(make_signal(5), "java-app-1")
    await incident_store.create(make_signal(10, {"service": "redis", "role": "cache"}), "redis-cache-1")

    for_java = await incident_store.list_by_target("java-app-1")

    assert [incident.id for incident in for_java] == [newer.id, older.id]


async def test_list_by_target_is_empty_for_an_unknown_target(incident_store):
    await incident_store.create(make_signal(), "java-app-1")

    assert await incident_store.list_by_target("no-such-target") == []


async def test_list_recent_is_bounded_and_most_recent_first(incident_store):
    created = [await incident_store.create(make_signal(offset), "java-app-1") for offset in range(5)]

    recent = await incident_store.list_recent(2)

    assert [incident.id for incident in recent] == [created[4].id, created[3].id]


async def test_unit_of_work_rolls_back_a_failed_transition(incident_store, monkeypatch):
    """The atomicity claim, tested rather than asserted in prose.

    A failure after both writes but before the commit must leave neither of them, or
    the denormalized state could drift from the log, which is the one thing ADR-0007
    exists to prevent.
    """
    incident = await incident_store.create(make_signal(), "java-app-1")

    async def fail_before_commit(self, session, incident_row):
        raise RuntimeError("simulated failure inside the unit of work")

    monkeypatch.setattr(SqlAlchemyIncidentStore, "_hydrate", fail_before_commit)

    with pytest.raises(RuntimeError):
        await incident_store.transition(
            incident.id,
            IncidentState.diagnosing,
            expected_version=incident.version,
            lease_generation=incident.lease_generation,
        )

    monkeypatch.undo()
    unchanged = await incident_store.get(incident.id)
    assert unchanged.state == IncidentState.received
    assert unchanged.version == 0
    assert await incident_store.list_transitions(incident.id) == []
