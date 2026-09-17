import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from yubarta.domain.signal import Signal
from yubarta.incident.errors import (
    AttemptNotFoundError,
    ConcurrentModificationError,
    DuplicateAttemptError,
    IncidentNotFoundError,
    IncidentStoreConsistencyError,
    StaleLeaseError,
)
from yubarta.incident.models import (
    AttemptApproval,
    AttemptOutcome,
    Incident,
    IncidentState,
    IncidentTransition,
    RemediationAttempt,
)
from yubarta.infra.db.orm import incident_transitions, incidents, remediation_attempts
from yubarta.infra.db.unit_of_work import SqlAlchemyUnitOfWork


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_attempt(row: RowMapping) -> RemediationAttempt:
    return RemediationAttempt(
        id=row["id"],
        incident_id=row["incident_id"],
        remediation_name=row["remediation_name"],
        idempotency_key=row["idempotency_key"],
        attempt_sequence=row["attempt_sequence"],
        approval_status=AttemptApproval(row["approval_status"]),
        approved_by=row["approved_by"],
        approved_at=row["approved_at"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        outcome=AttemptOutcome(row["outcome"]) if row["outcome"] else None,
        evidence=row["evidence"],
    )


def _to_transition(row: RowMapping) -> IncidentTransition:
    return IncidentTransition(
        id=row["id"],
        incident_id=row["incident_id"],
        from_state=IncidentState(row["from_state"]),
        to_state=IncidentState(row["to_state"]),
        occurred_at=row["occurred_at"],
    )


def _to_incident(row: RowMapping, attempts: list[RemediationAttempt]) -> Incident:
    return Incident(
        id=row["id"],
        signal=Signal(**row["signal_raw"]),
        target_name=row["target_name"],
        state=IncidentState(row["state"]),
        version=row["version"],
        lease_owner=row["lease_owner"],
        lease_generation=row["lease_generation"],
        lease_expires_at=row["lease_expires_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        attempts=attempts,
    )


class SqlAlchemyIncidentStore:
    """Postgres-backed `IncidentStore`.

    Every method runs inside one unit of work, so a committed transition or attempt
    is immediately durable and readable back, and a transition's state update can
    never land without its transition-log row.
    """

    def __init__(self, unit_of_work: SqlAlchemyUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def create(self, signal: Signal, target_name: str) -> Incident:
        now = _now()
        insert_incident = (
            pg_insert(incidents)
            .values(
                id=str(uuid.uuid4()),
                signal_id=signal.id,
                signal_fingerprint=signal.fingerprint,
                signal_raw=signal.model_dump(mode="json"),
                target_name=target_name,
                state=IncidentState.received.value,
                version=0,
                lease_owner=None,
                lease_generation=0,
                lease_expires_at=None,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_nothing(index_elements=["signal_id"])
        )
        async with self._unit_of_work.begin() as session:
            await session.execute(insert_incident)
            # A conflicting signal_id inserts nothing; the re-read returns the
            # incident that won. A concurrent inserter blocks this statement on the
            # unique index until it commits, so the row is visible by the time the
            # conflict is resolved.
            result = await session.execute(select(incidents).where(incidents.c.signal_id == signal.id))
            row = result.mappings().first()
            if row is None:
                raise IncidentStoreConsistencyError(signal.id)
            return await self._hydrate(session, row)

    async def transition(
        self,
        incident_id: str,
        to_state: IncidentState,
        expected_version: int,
        lease_generation: int,
    ) -> Incident:
        now = _now()
        async with self._unit_of_work.begin() as session:
            # Read the current state to log the transition's origin. This is not a
            # lock and carries no guarantee on its own: the conditional UPDATE below
            # is what enforces correctness. It is still the right `from_state`
            # whenever that UPDATE succeeds, because any writer committing in
            # between would have moved `version` and made the UPDATE match no rows.
            current = await session.execute(
                select(incidents.c.state).where(incidents.c.id == incident_id)
            )
            from_state = current.scalar_one_or_none()
            if from_state is None:
                raise IncidentNotFoundError(incident_id)

            applied = await session.execute(
                update(incidents)
                .where(
                    incidents.c.id == incident_id,
                    incidents.c.version == expected_version,
                    incidents.c.lease_generation == lease_generation,
                )
                .values(
                    state=to_state.value,
                    version=incidents.c.version + 1,
                    updated_at=now,
                )
            )
            if applied.rowcount == 0:
                await self._reject_transition(session, incident_id, expected_version, lease_generation)

            await session.execute(
                insert(incident_transitions).values(
                    id=str(uuid.uuid4()),
                    incident_id=incident_id,
                    from_state=from_state,
                    to_state=to_state.value,
                    occurred_at=now,
                )
            )
            updated = await session.execute(select(incidents).where(incidents.c.id == incident_id))
            row = updated.mappings().one()
            return await self._hydrate(session, row)

    async def record_attempt(
        self,
        incident_id: str,
        remediation_name: str,
        approval_status: AttemptApproval = AttemptApproval.not_required,
    ) -> RemediationAttempt:
        now = _now()
        idempotency_key = ""
        try:
            async with self._unit_of_work.begin() as session:
                exists = await session.execute(select(incidents.c.id).where(incidents.c.id == incident_id))
                if exists.scalar_one_or_none() is None:
                    raise IncidentNotFoundError(incident_id)

                # The in-flight attempt keeps the same sequence (and therefore the
                # same key) until it completes, so a crash-and-retry with the same
                # inputs collides instead of executing the remediation again.
                completed = await session.execute(
                    select(func.count())
                    .select_from(remediation_attempts)
                    .where(
                        remediation_attempts.c.incident_id == incident_id,
                        remediation_attempts.c.remediation_name == remediation_name,
                        remediation_attempts.c.outcome.isnot(None),
                    )
                )
                attempt_sequence = int(completed.scalar_one()) + 1
                idempotency_key = f"{incident_id}:{remediation_name}:{attempt_sequence}"

                existing = await self._read_attempt_by_key(session, idempotency_key)
                if existing is not None:
                    raise DuplicateAttemptError(idempotency_key, existing)

                recorded = await session.execute(
                    insert(remediation_attempts)
                    .values(
                        id=str(uuid.uuid4()),
                        incident_id=incident_id,
                        remediation_name=remediation_name,
                        idempotency_key=idempotency_key,
                        attempt_sequence=attempt_sequence,
                        approval_status=approval_status.value,
                        approved_by=None,
                        approved_at=None,
                        started_at=now,
                        completed_at=None,
                        outcome=None,
                        evidence=None,
                    )
                    .returning(*remediation_attempts.c)
                )
                return _to_attempt(recorded.mappings().one())
        except IntegrityError as error:
            # Two writers computed the same key and raced past the check above. The
            # unique constraint let one win; this is the loser. The integrity error
            # never escapes the store, the caller gets the attempt that won.
            winner = await self._find_attempt_by_key(idempotency_key)
            if winner is None:
                raise
            raise DuplicateAttemptError(idempotency_key, winner) from error

    async def resolve_approval(
        self,
        attempt_id: str,
        approval_status: AttemptApproval,
        approved_by: str | None,
    ) -> RemediationAttempt:
        async with self._unit_of_work.begin() as session:
            resolved = await session.execute(
                update(remediation_attempts)
                .where(remediation_attempts.c.id == attempt_id)
                .values(
                    approval_status=approval_status.value,
                    approved_by=approved_by,
                    approved_at=_now(),
                )
                .returning(*remediation_attempts.c)
            )
            row = resolved.mappings().first()
            if row is None:
                raise AttemptNotFoundError(attempt_id)
            return _to_attempt(row)

    async def complete_attempt(
        self,
        attempt_id: str,
        outcome: AttemptOutcome,
        evidence: dict[str, Any] | None,
    ) -> RemediationAttempt:
        async with self._unit_of_work.begin() as session:
            completed = await session.execute(
                update(remediation_attempts)
                .where(remediation_attempts.c.id == attempt_id)
                .values(outcome=outcome.value, evidence=evidence, completed_at=_now())
                .returning(*remediation_attempts.c)
            )
            row = completed.mappings().first()
            if row is None:
                raise AttemptNotFoundError(attempt_id)
            return _to_attempt(row)

    async def get(self, incident_id: str) -> Incident | None:
        async with self._unit_of_work.begin() as session:
            result = await session.execute(select(incidents).where(incidents.c.id == incident_id))
            row = result.mappings().first()
            if row is None:
                return None
            return await self._hydrate(session, row)

    async def list_transitions(self, incident_id: str) -> list[IncidentTransition]:
        async with self._unit_of_work.begin() as session:
            result = await session.execute(
                select(incident_transitions)
                .where(incident_transitions.c.incident_id == incident_id)
                .order_by(incident_transitions.c.occurred_at, incident_transitions.c.id)
            )
            return [_to_transition(row) for row in result.mappings().all()]

    async def list_by_target(self, target_name: str) -> list[Incident]:
        async with self._unit_of_work.begin() as session:
            result = await session.execute(
                select(incidents)
                .where(incidents.c.target_name == target_name)
                .order_by(incidents.c.created_at.desc())
            )
            return [await self._hydrate(session, row) for row in result.mappings().all()]

    async def list_recent(self, limit: int) -> list[Incident]:
        async with self._unit_of_work.begin() as session:
            result = await session.execute(
                select(incidents).order_by(incidents.c.created_at.desc()).limit(limit)
            )
            return [await self._hydrate(session, row) for row in result.mappings().all()]

    async def _reject_transition(
        self,
        session: AsyncSession,
        incident_id: str,
        expected_version: int,
        lease_generation: int,
    ) -> None:
        """Classify a transition the conditional UPDATE refused to apply.

        The lease is checked first: a superseded owner is rejected even when its
        expected version matches, which is the case that keeps the fencing token
        from collapsing into the version guard (ADR-0006).
        """
        result = await session.execute(
            select(incidents.c.version, incidents.c.lease_generation).where(incidents.c.id == incident_id)
        )
        row = result.first()
        if row is None:
            raise IncidentNotFoundError(incident_id)
        persisted_version, persisted_generation = row
        if persisted_generation != lease_generation:
            raise StaleLeaseError(incident_id, lease_generation, persisted_generation)
        raise ConcurrentModificationError(incident_id, expected_version, persisted_version)

    async def _hydrate(self, session: AsyncSession, incident_row: RowMapping) -> Incident:
        result = await session.execute(
            select(remediation_attempts)
            .where(remediation_attempts.c.incident_id == incident_row["id"])
            .order_by(remediation_attempts.c.attempt_sequence, remediation_attempts.c.started_at)
        )
        attempts = [_to_attempt(row) for row in result.mappings().all()]
        return _to_incident(incident_row, attempts)

    async def _read_attempt_by_key(self, session: AsyncSession, idempotency_key: str) -> RemediationAttempt | None:
        result = await session.execute(
            select(remediation_attempts).where(remediation_attempts.c.idempotency_key == idempotency_key)
        )
        row = result.mappings().first()
        return _to_attempt(row) if row is not None else None

    async def _find_attempt_by_key(self, idempotency_key: str) -> RemediationAttempt | None:
        """Read an attempt in its own unit of work, for use after a failed one."""
        async with self._unit_of_work.begin() as session:
            return await self._read_attempt_by_key(session, idempotency_key)
