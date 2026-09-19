"""Incident lifecycle. External operations run outside database transactions."""

import asyncio
import logging
from datetime import UTC, datetime

from yubarta.config.settings import AppConfig
from yubarta.controllers.checks import ChecksRunner
from yubarta.controllers.diagnostics import DiagnosticsRunner
from yubarta.controllers.remediations.runner import RemediationRunner
from yubarta.controllers.unit_of_work import UnitOfWorkFactory
from yubarta.core.enums import IncidentState, StepKind, StepState
from yubarta.core.interfaces import IncidentRepository
from yubarta.core.models import CheckOutcome, Incident, IncidentDetail, NormalizedEvent
from yubarta.core.rules import RuleEngine


class IncidentService:
    def __init__(
        self,
        config: AppConfig,
        uow_factory: UnitOfWorkFactory,
        rules: RuleEngine,
        diagnostics: DiagnosticsRunner,
        checks: ChecksRunner,
        remediations: RemediationRunner,
    ) -> None:
        self._config = config
        self._uow_factory = uow_factory
        self._rules = rules
        self._diagnostics = diagnostics
        self._checks = checks
        self._remediations = remediations
        self._locks: dict[str, asyncio.Lock] = {}
        self._logger = logging.getLogger(__name__)

    async def list_incidents(self, limit: int = 50) -> list[Incident]:
        async with self._uow_factory() as uow:
            return await uow.incidents.list_incidents(limit)

    async def get_incident(self, incident_id: str) -> IncidentDetail | None:
        async with self._uow_factory() as uow:
            incident = await uow.incidents.get(incident_id)
            if incident is None:
                return None
            return IncidentDetail(
                incident,
                await uow.incidents.list_steps(incident_id),
                await uow.incidents.list_transitions(incident_id),
            )

    async def handle_event(self, event: NormalizedEvent) -> str | None:
        incident_type = self._rules.evaluate(event)
        if incident_type is None:
            return None
        key = f"{event.target}|{incident_type}"
        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            async with self._uow_factory() as uow:
                incident, created = await uow.incidents.get_or_create_active(event.target, incident_type)
                await uow.incidents.add_trigger_event(incident.id, event)
                await uow.commit()
            if created:
                try:
                    await self._run_lifecycle(incident.id)
                except Exception as exc:
                    # One failed incident must not stop observation of the target.
                    self._logger.exception("Incident %s processing failed", incident.id)
                    try:
                        await self._fail(incident.id, str(exc))
                    except Exception:
                        self._logger.exception("Could not record failure for incident %s", incident.id)
            return incident.id

    async def _get(self, repository: IncidentRepository, incident_id: str) -> Incident:
        incident = await repository.get(incident_id)
        if incident is None:
            raise ValueError(f"Incident not found: {incident_id}")
        return incident

    async def _transition(self, incident_id: str, state: IncidentState, reason: str) -> None:
        async with self._uow_factory() as uow:
            incident = await self._get(uow.incidents, incident_id)
            await uow.incidents.transition_state(incident.id, incident.version, state, reason)
            await uow.commit()

    async def _fail(self, incident_id: str, reason: str) -> None:
        async with self._uow_factory() as uow:
            incident = await self._get(uow.incidents, incident_id)
            if incident.state in (IncidentState.RESOLVED, IncidentState.FAILED):
                return
            # Diagnosis failures pass through PRECHECKING, where failure is legal.
            if incident.state == IncidentState.DETECTED:
                incident = await uow.incidents.transition_state(
                    incident.id, incident.version, IncidentState.DIAGNOSING, reason
                )
            if incident.state == IncidentState.DIAGNOSING:
                incident = await uow.incidents.transition_state(
                    incident.id, incident.version, IncidentState.PRECHECKING, reason
                )
            if incident.state == IncidentState.REMEDIATING:
                incident = await uow.incidents.transition_state(
                    incident.id, incident.version, IncidentState.VERIFYING, reason
                )
            await uow.incidents.mark_failed(incident.id, incident.version, reason)
            await uow.commit()

    async def _diagnose(self, incident_id: str) -> None:
        await self._transition(incident_id, IncidentState.DIAGNOSING, "start diagnostics")
        results = await self._diagnostics.run_all()
        async with self._uow_factory() as uow:
            for result in results:
                step = await uow.incidents.add_step(incident_id, StepKind.DIAGNOSTIC, result.name)
                await uow.incidents.update_step(
                    step.id,
                    state=StepState.SUCCEEDED.value if result.ok and result.exit_code == 0 else StepState.FAILED.value,
                    started_at=datetime.now(UTC),
                    finished_at=datetime.now(UTC),
                    exit_code=result.exit_code,
                    stdout_excerpt=result.stdout,
                    stderr_excerpt=result.stderr,
                )
            incident = await self._get(uow.incidents, incident_id)
            await uow.incidents.transition_state(
                incident.id, incident.version, IncidentState.PRECHECKING, "diagnostics done"
            )
            await uow.commit()

    async def _record_checks(
        self,
        repository: IncidentRepository,
        incident_id: str,
        kind: StepKind,
        outcomes: list[CheckOutcome],
        remediation: str | None = None,
    ) -> None:
        for outcome in outcomes:
            step = await repository.add_step(incident_id, kind, outcome.name)
            result = {"passed": outcome.passed, "detail": outcome.detail}
            if remediation is not None:
                result = {"passed": outcome.passed, "after": remediation}
            await repository.update_step(
                step.id,
                state=StepState.SUCCEEDED.value if outcome.passed else StepState.FAILED.value,
                started_at=datetime.now(UTC),
                finished_at=datetime.now(UTC),
                exit_code=outcome.exit_code,
                stdout_excerpt=outcome.detail,
                result=result,
            )

    async def _precheck(self, incident_id: str) -> bool:
        healthy, outcomes = await self._checks.run_once()
        async with self._uow_factory() as uow:
            await self._record_checks(uow.incidents, incident_id, StepKind.PRECHECK, outcomes)
            incident = await self._get(uow.incidents, incident_id)
            if healthy:
                await uow.incidents.mark_resolved(incident.id, incident.version, None, "precheck healthy")
            else:
                await uow.incidents.transition_state(
                    incident.id, incident.version, IncidentState.REMEDIATING, "precheck unhealthy"
                )
            await uow.commit()
        return healthy

    async def _run_lifecycle(self, incident_id: str) -> None:
        await self._diagnose(incident_id)
        if await self._precheck(incident_id):
            return
        for index, remediation in enumerate(self._config.remediations):
            async with self._uow_factory() as uow:
                step = await uow.incidents.add_step(incident_id, StepKind.REMEDIATION, remediation.name)
                await uow.incidents.update_step(step.id, state=StepState.RUNNING.value, started_at=datetime.now(UTC))
                await uow.commit()

            outcome = await self._remediations.run(remediation)
            async with self._uow_factory() as uow:
                output: dict[str, object] = {}
                if outcome.state != StepState.SKIPPED:
                    output = {
                        "exit_code": outcome.result.exit_code if outcome.result else None,
                        "stdout_excerpt": outcome.result.stdout if outcome.result else "",
                        "stderr_excerpt": outcome.result.stderr if outcome.result else "",
                    }
                await uow.incidents.update_step(
                    step.id,
                    state=outcome.state.value,
                    finished_at=datetime.now(UTC),
                    error=outcome.error,
                    **output,
                )
                await uow.commit()
            if outcome.state == StepState.SKIPPED:
                continue
            if outcome.state == StepState.FAILED:
                if index == len(self._config.remediations) - 1:
                    await self._fail(incident_id, outcome.error or f"remediation {remediation.name} failed")
                    return
                continue
            if await self._verify(incident_id, step.id, remediation.name):
                return
        reason = (
            "exhausted remediations without recovery" if self._remediations.apply else "dry-run: remediations skipped"
        )
        await self._fail(incident_id, reason)

    async def _verify(self, incident_id: str, step_id: str, remediation: str) -> bool:
        await self._transition(incident_id, IncidentState.VERIFYING, f"verify after {remediation}")
        healthy, outcomes = await self._checks.verify(self._config.verify)
        async with self._uow_factory() as uow:
            await self._record_checks(uow.incidents, incident_id, StepKind.VERIFICATION, outcomes, remediation)
            incident = await self._get(uow.incidents, incident_id)
            if healthy:
                await uow.incidents.mark_resolved(
                    incident.id, incident.version, step_id, f"recovered after {remediation}"
                )
            else:
                await uow.incidents.transition_state(
                    incident.id, incident.version, IncidentState.REMEDIATING, f"still unhealthy after {remediation}"
                )
            await uow.commit()
        return healthy
