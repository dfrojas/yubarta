import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from yubarta.domain.signal import Signal
from yubarta.incident.errors import (
    AttemptNotFoundError,
    DuplicateAttemptError,
    IncidentNotFoundError,
    IncidentStoreConsistencyError,
)
from yubarta.incident.models import (
    AttemptApproval,
    AttemptOutcome,
    Incident,
    IncidentState,
    RemediationAttempt,
)
from yubarta.infra.db.orm import incident_transitions, incidents, remediation_attempts


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


def _to_incident(row: RowMapping, attempts: list[RemediationAttempt]) -> Incident:
    return Incident(
        id=row["id"],
        signal=Signal(**row["signal_raw"]),
        target_name=row["target_name"],
        state=IncidentState(row["state"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        attempts=attempts,
    )


class SqlAlchemyIncidentStore:
    """Postgres-backed `IncidentStore`. Write methods commit their own unit of work
    so a committed transition or attempt is immediately durable and readable back.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

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
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_nothing(index_elements=["signal_id"])
        )
        await self._session.execute(insert_incident)
        await self._session.commit()
        # A conflicting signal_id inserts nothing; re-read returns the existing incident.
        result = await self._session.execute(select(incidents).where(incidents.c.signal_id == signal.id))
        row = result.mappings().first()
        if row is None:
            raise IncidentStoreConsistencyError(signal.id)
        return await self._hydrate(row)

    async def transition(self, incident_id: str, to_state: IncidentState) -> Incident:
        now = _now()
        # Row lock serializes concurrent transitions on the same incident: a second
        # writer waits for this transaction to commit, then transitions from the
        # state this one left, so no transition is silently lost.
        locked = await self._session.execute(
            select(incidents).where(incidents.c.id == incident_id).with_for_update()
        )
        row = locked.mappings().first()
        if row is None:
            raise IncidentNotFoundError(incident_id)
        from_state = str(row["state"])

        await self._session.execute(
            update(incidents)
            .where(incidents.c.id == incident_id)
            .values(state=to_state.value, updated_at=now)
        )
        await self._session.execute(
            insert(incident_transitions).values(
                id=str(uuid.uuid4()),
                incident_id=incident_id,
                from_state=from_state,
                to_state=to_state.value,
                occurred_at=now,
            )
        )
        await self._session.commit()
        incident = await self.get(incident_id)
        if incident is None:
            raise IncidentNotFoundError(incident_id)
        return incident

    async def record_attempt(
        self,
        incident_id: str,
        remediation_name: str,
        approval_status: AttemptApproval = AttemptApproval.not_required,
    ) -> RemediationAttempt:
        now = _now()
        if await self.get(incident_id) is None:
            raise IncidentNotFoundError(incident_id)

        # The in-flight attempt keeps the same sequence (and key) until it completes,
        # so a crash-and-retry with the same inputs collides instead of re-running.
        completed = await self._session.execute(
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

        existing = await self._session.execute(
            select(remediation_attempts.c.outcome).where(
                remediation_attempts.c.idempotency_key == idempotency_key
            )
        )
        existing_row = existing.first()
        if existing_row is not None and existing_row[0] is None:
            raise DuplicateAttemptError(idempotency_key)

        attempt_id = str(uuid.uuid4())
        await self._session.execute(
            insert(remediation_attempts).values(
                id=attempt_id,
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
        )
        await self._session.commit()
        return await self._require_attempt(attempt_id)

    async def resolve_approval(
        self,
        attempt_id: str,
        approval_status: AttemptApproval,
        approved_by: str | None,
    ) -> RemediationAttempt:
        result = await self._session.execute(
            update(remediation_attempts)
            .where(remediation_attempts.c.id == attempt_id)
            .values(approval_status=approval_status.value, approved_by=approved_by, approved_at=_now())
        )
        if result.rowcount == 0:
            raise AttemptNotFoundError(attempt_id)
        await self._session.commit()
        return await self._require_attempt(attempt_id)

    async def complete_attempt(
        self,
        attempt_id: str,
        outcome: AttemptOutcome,
        evidence: dict[str, Any] | None,
    ) -> RemediationAttempt:
        result = await self._session.execute(
            update(remediation_attempts)
            .where(remediation_attempts.c.id == attempt_id)
            .values(outcome=outcome.value, evidence=evidence, completed_at=_now())
        )
        if result.rowcount == 0:
            raise AttemptNotFoundError(attempt_id)
        await self._session.commit()
        return await self._require_attempt(attempt_id)

    async def get(self, incident_id: str) -> Incident | None:
        result = await self._session.execute(select(incidents).where(incidents.c.id == incident_id))
        row = result.mappings().first()
        if row is None:
            return None
        return await self._hydrate(row)

    async def list_by_target(self, target_name: str) -> list[Incident]:
        result = await self._session.execute(
            select(incidents)
            .where(incidents.c.target_name == target_name)
            .order_by(incidents.c.created_at.desc())
        )
        return [await self._hydrate(row) for row in result.mappings().all()]

    async def list_recent(self, limit: int) -> list[Incident]:
        result = await self._session.execute(
            select(incidents).order_by(incidents.c.created_at.desc()).limit(limit)
        )
        return [await self._hydrate(row) for row in result.mappings().all()]

    async def _hydrate(self, incident_row: RowMapping) -> Incident:
        result = await self._session.execute(
            select(remediation_attempts)
            .where(remediation_attempts.c.incident_id == incident_row["id"])
            .order_by(remediation_attempts.c.attempt_sequence, remediation_attempts.c.started_at)
        )
        attempts = [_to_attempt(row) for row in result.mappings().all()]
        return _to_incident(incident_row, attempts)

    async def _require_attempt(self, attempt_id: str) -> RemediationAttempt:
        result = await self._session.execute(
            select(remediation_attempts).where(remediation_attempts.c.id == attempt_id)
        )
        row = result.mappings().first()
        if row is None:
            raise AttemptNotFoundError(attempt_id)
        return _to_attempt(row)
