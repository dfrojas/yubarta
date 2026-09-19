"""Incident service: detect -> diagnostics -> precheck -> remediation -> verify loop."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from yubarta.checks.runner import run_all_checks, run_checks_once
from yubarta.config import AppConfig
from yubarta.diagnostics.runner import DiagnosticsRunner
from yubarta.events.models import NormalizedEvent
from yubarta.execution.ssh import SSHConnectionFactory
from yubarta.incidents.models import StepKind, StepState
from yubarta.incidents.state_machine import IncidentState
from yubarta.persistence.repository import IncidentRepository
from yubarta.rules.engine import RuleEngine

logger = logging.getLogger("yubarta")


class IncidentService:
    def __init__(
        self,
        config: AppConfig,
        session_factory: async_sessionmaker[AsyncSession],
        rules: RuleEngine,
        executor: SSHConnectionFactory,
        diagnostics: DiagnosticsRunner,
        apply: bool = False,
    ) -> None:
        self._config = config
        self._sessions = session_factory
        self._rules = rules
        self._executor = executor
        self._diagnostics = diagnostics
        self._apply = apply
        self._locks: dict[str, asyncio.Lock] = {}

    def _lock_for(self, key: str) -> asyncio.Lock:
        lock = self._locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[key] = lock
        return lock

    async def handle_event(self, event: NormalizedEvent) -> str | None:
        incident_type = self._rules.evaluate(event)
        if incident_type is None:
            return None
        key = f"{event.target}|{incident_type}"
        async with self._lock_for(key):
            async with self._sessions() as session:
                repo = IncidentRepository(session)
                incident, created = await repo.get_or_create_active(event.target, incident_type)
                await repo.add_trigger_event(incident.id, event)
                await session.commit()
                incident_id = incident.id
                is_new = created
            if is_new:
                await self._process_incident(incident_id)
            return incident_id

    async def _process_incident(self, incident_id: str) -> None:
        try:
            await self._run_lifecycle(incident_id)
        except Exception as exc:
            logger.exception("Incident %s processing failed: %s", incident_id, exc)
            try:
                async with self._sessions() as session:
                    repo = IncidentRepository(session)
                    row = await repo.get(incident_id)
                    if row is not None and row.state not in ("RESOLVED", "FAILED"):
                        # best-effort failure marking through legal transitions
                        for target in (IncidentState.FAILED,):
                            try:
                                await repo.transition_state(row.id, row.version, target, str(exc))
                                row = await repo.get(incident_id)
                                if row is None:
                                    break
                            except Exception:
                                break
                        await session.commit()
            except Exception:
                pass

    async def _run_lifecycle(self, incident_id: str) -> None:
        # DETECTED -> DIAGNOSING
        async with self._sessions() as session:
            repo = IncidentRepository(session)
            row = await repo.get(incident_id)
            assert row is not None
            row = await repo.transition_state(row.id, row.version, IncidentState.DIAGNOSING, "start diagnostics")
            await session.commit()

        # Diagnostics (best-effort, persisted)
        diag_results = await self._diagnostics.run_all()
        async with self._sessions() as session:
            repo = IncidentRepository(session)
            row = await repo.get(incident_id)
            assert row is not None
            for result in diag_results:
                step = await repo.add_step(row.id, StepKind.DIAGNOSTIC, result.name)
                await repo.update_step(
                    step.id,
                    state=StepState.SUCCEEDED.value if result.ok and result.exit_code == 0 else StepState.FAILED.value,
                    started_at=datetime.now(UTC),
                    finished_at=datetime.now(UTC),
                    exit_code=result.exit_code,
                    stdout_excerpt=result.stdout,
                    stderr_excerpt=result.stderr,
                )
            row = await repo.transition_state(row.id, row.version, IncidentState.PRECHECKING, "diagnostics done")
            await session.commit()

        # Precheck
        healthy, outcomes = await run_checks_once(self._config.checks, self._executor)
        async with self._sessions() as session:
            repo = IncidentRepository(session)
            row = await repo.get(incident_id)
            assert row is not None
            for outcome in outcomes:
                step = await repo.add_step(row.id, StepKind.PRECHECK, outcome.name)
                await repo.update_step(
                    step.id,
                    state=StepState.SUCCEEDED.value if outcome.passed else StepState.FAILED.value,
                    started_at=datetime.now(UTC),
                    finished_at=datetime.now(UTC),
                    exit_code=outcome.exit_code,
                    stdout_excerpt=outcome.detail,
                    result={"passed": outcome.passed, "detail": outcome.detail},
                )
            if healthy:
                row = await repo.transition_state(row.id, row.version, IncidentState.RESOLVED, "precheck healthy")
                row.resolved_at = datetime.now(UTC)
                row.resolved_by_step_id = None
                await session.commit()
                return
            row = await repo.transition_state(row.id, row.version, IncidentState.REMEDIATING, "precheck unhealthy")
            await session.commit()

        # Remediation loop in YAML order
        for remediation in self._config.remediations:
            async with self._sessions() as session:
                repo = IncidentRepository(session)
                row = await repo.get(incident_id)
                assert row is not None
                remediation_step = await repo.add_step(row.id, StepKind.REMEDIATION, remediation.name)
                await repo.update_step(
                    remediation_step.id,
                    state=StepState.RUNNING.value,
                    started_at=datetime.now(UTC),
                )
                await session.commit()
                remediation_step_id = remediation_step.id

            if not self._apply:
                async with self._sessions() as session:
                    repo = IncidentRepository(session)
                    await repo.update_step(
                        remediation_step_id,
                        state=StepState.SKIPPED.value,
                        finished_at=datetime.now(UTC),
                        error="dry-run: remediation skipped",
                    )
                    await session.commit()
                continue

            # Execute remediation
            try:
                outcome = await self._executor.run(remediation.command, timeout=300.0)
                remediation_ok = outcome.exit_code == 0
                remediation_error = None if remediation_ok else f"exit={outcome.exit_code}"
            except Exception as exc:
                outcome = None
                remediation_ok = False
                remediation_error = str(exc)

            async with self._sessions() as session:
                repo = IncidentRepository(session)
                row = await repo.get(incident_id)
                assert row is not None
                await repo.update_step(
                    remediation_step_id,
                    state=StepState.SUCCEEDED.value if remediation_ok else StepState.FAILED.value,
                    finished_at=datetime.now(UTC),
                    exit_code=outcome.exit_code if outcome else None,
                    stdout_excerpt=outcome.stdout if outcome else "",
                    stderr_excerpt=outcome.stderr if outcome else "",
                    error=remediation_error,
                )
                if not remediation_ok:
                    # remediation command failed: record and move to next remediation if any,
                    # else fail the incident through VERIFYING->FAILED path legally.
                    remaining = self._config.remediations[
                        [item.name for item in self._config.remediations].index(remediation.name) + 1 :
                    ]
                    if not remaining:
                        row = await repo.transition_state(
                            row.id, row.version, IncidentState.VERIFYING, f"remediation {remediation.name} failed"
                        )
                        row = await repo.transition_state(
                            row.id,
                            row.version,
                            IncidentState.FAILED,
                            f"remediation {remediation.name} failed: {remediation_error}",
                        )
                        row.failure_reason = remediation_error
                    await session.commit()
                    continue
                row = await repo.transition_state(
                    row.id, row.version, IncidentState.VERIFYING, f"verify after {remediation.name}"
                )
                await session.commit()

            # Verification with convergence
            healthy, verify_outcomes = await run_all_checks(
                self._config.checks,
                self._executor,
                settle_delay=self._config.verify.settle_delay,
                interval=self._config.verify.interval,
                timeout=self._config.verify.timeout,
            )
            async with self._sessions() as session:
                repo = IncidentRepository(session)
                row = await repo.get(incident_id)
                assert row is not None
                for verify_outcome in verify_outcomes:
                    verify_step = await repo.add_step(row.id, StepKind.VERIFICATION, verify_outcome.name)
                    await repo.update_step(
                        verify_step.id,
                        state=StepState.SUCCEEDED.value if verify_outcome.passed else StepState.FAILED.value,
                        started_at=datetime.now(UTC),
                        finished_at=datetime.now(UTC),
                        exit_code=verify_outcome.exit_code,
                        stdout_excerpt=verify_outcome.detail,
                        result={"passed": verify_outcome.passed, "after": remediation.name},
                    )
                if healthy:
                    row = await repo.transition_state(
                        row.id, row.version, IncidentState.RESOLVED, f"recovered after {remediation.name}"
                    )
                    row.resolved_at = datetime.now(UTC)
                    row.resolved_by_step_id = remediation_step_id
                    await session.commit()
                    return
                # still unhealthy -> back to REMEDIATING for next remediation
                row = await repo.transition_state(
                    row.id, row.version, IncidentState.REMEDIATING, f"still unhealthy after {remediation.name}"
                )
                await session.commit()

        # Exhausted remediations (or dry-run): fail unless dry-run semantics say otherwise.
        async with self._sessions() as session:
            repo = IncidentRepository(session)
            row = await repo.get(incident_id)
            if row is None:
                return
            if row.state in ("RESOLVED", "FAILED"):
                return
            if not self._apply:
                # dry-run: leave a clear terminal marker without touching target verified state
                try:
                    current = IncidentState(row.state)
                    if current == IncidentState.REMEDIATING:
                        row = await repo.transition_state(
                            row.id, row.version, IncidentState.VERIFYING, "dry-run verification"
                        )
                    row = await repo.transition_state(
                        row.id, row.version, IncidentState.FAILED, "dry-run: remediations skipped"
                    )
                    row.failure_reason = "dry-run: remediations skipped"
                except Exception:
                    pass
                await session.commit()
                return
            try:
                current = IncidentState(row.state)
                if current == IncidentState.REMEDIATING:
                    row = await repo.transition_state(
                        row.id, row.version, IncidentState.VERIFYING, "exhausted remediations"
                    )
                    current = IncidentState.VERIFYING
                if current == IncidentState.VERIFYING:
                    row = await repo.transition_state(
                        row.id, row.version, IncidentState.FAILED, "exhausted remediations"
                    )
                    row.failure_reason = "exhausted remediations without recovery"
            except Exception:
                pass
            await session.commit()
