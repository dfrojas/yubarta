import asyncio
import logging
from collections.abc import Awaitable, Callable
from uuid import UUID

from yubarta.config.settings import AppConfig, CommandCheck, Watch
from yubarta.controllers.checks import Checks
from yubarta.controllers.diagnostics import Diagnostics
from yubarta.controllers.remediations.runner import Remediations
from yubarta.controllers.unit_of_work import UnitOfWork
from yubarta.core.enums import IncidentState, StepKind
from yubarta.core.models import ExecutionResult, Incident, IncidentDetail, NormalizedEvent, Step
from yubarta.core.rules import match_event


class Incidents:
    def __init__(self, config: AppConfig, uow: Callable[[], UnitOfWork], diagnostics: Diagnostics,
                 checks: Checks, remediations: Remediations):
        self.config = config
        self.uow = uow
        self.diagnostics = diagnostics
        self.checks = checks
        self.remediations = remediations
        self.accepting = True
        self.ingestion_lock = asyncio.Lock()
        # ponytail: one target executes one incident at a time; use target locks for fleet support.
        self.execution_lock = asyncio.Lock()
        self.tasks: set[asyncio.Task[None]] = set()
        self.logger = logging.getLogger(__name__)

    async def ingest(self, event: NormalizedEvent, watch: Watch) -> None:
        incident_type = match_event(event, watch)
        if not self.accepting or incident_type is None:
            return
        async with self.ingestion_lock:
            async with self.uow() as work:
                incident, created = await work.repository.record_event(event, incident_type)
            if incident is not None and created:
                task = asyncio.create_task(self.process(incident), name=f"incident:{incident.id}")
                self.tasks.add(task)
                task.add_done_callback(self.tasks.discard)

    async def transition(self, incident: Incident, state: IncidentState, reason: str,
                         resolved_by: UUID | None = None) -> Incident:
        async with self.uow() as work:
            return await work.repository.transition(incident, state, reason, resolved_by)

    async def step(self, incident: Incident, kind: StepKind, name: str,
                   operation: Callable[[], Awaitable[ExecutionResult]], skipped: bool = False) -> tuple[Step, ExecutionResult]:
        async with self.uow() as work:
            step = await work.repository.start_step(incident.id, kind, name)
        result = await operation()
        async with self.uow() as work:
            step = await work.repository.finish_step(step, result, skipped)
        return step, result

    async def run_checks(self, incident: Incident, kind: StepKind, deadline: float | None = None) -> bool:
        results = []
        for configured in self.config.checks:
            check = configured
            if deadline is not None:
                remaining = max(0.001, deadline - asyncio.get_running_loop().time())
                check = check.model_copy(update={"timeout": min(check.timeout, remaining)})
            name = check.run if isinstance(check, CommandCheck) else check.http
            _, result = await self.step(incident, kind, name, lambda: self.checks.run(check))
            results.append(result.passed)
        return all(results)

    async def verify(self, incident: Incident) -> bool:
        config = self.config.verify
        await asyncio.sleep(config.settle_delay)
        deadline = asyncio.get_running_loop().time() + config.timeout
        while True:
            if await self.run_checks(incident, StepKind.VERIFICATION, deadline):
                return True
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                return False
            await asyncio.sleep(min(config.interval, remaining))

    async def process(self, incident: Incident) -> None:
        try:
            async with self.execution_lock:
                incident = await self.transition(incident, IncidentState.DIAGNOSING, "Collect diagnostics")
                for command in self.config.diagnostics:
                    await self.step(incident, StepKind.DIAGNOSTIC, command, lambda: self.diagnostics.run(command))
                incident = await self.transition(incident, IncidentState.PRECHECKING, "Check current health")
                if await self.run_checks(incident, StepKind.PRECHECK):
                    await self.transition(incident, IncidentState.RESOLVED, "Healthy before remediation")
                    return
                incident = await self.transition(incident, IncidentState.REMEDIATING, "Precheck unhealthy")
                for remediation in self.config.remediations:
                    step, result = await self.step(incident, StepKind.REMEDIATION, remediation.name,
                        lambda: self.remediations.run(remediation), skipped=not self.remediations.apply)
                    if not self.remediations.apply:
                        continue
                    if remediation.required and result.error:
                        await self.transition(incident, IncidentState.FAILED, f"Required remediation unavailable: {remediation.name}")
                        return
                    incident = await self.transition(incident, IncidentState.VERIFYING, f"Verify after {remediation.name}")
                    if await self.verify(incident):
                        await self.transition(incident, IncidentState.RESOLVED, f"Recovery verified after {remediation.name}", step.id)
                        return
                    incident = await self.transition(incident, IncidentState.REMEDIATING, "Checks remain unhealthy")
                reason = "Remediations exhausted" if self.remediations.apply else "Dry-run: remediations skipped"
                await self.transition(incident, IncidentState.FAILED, reason)
        except asyncio.CancelledError:
            await self.fail_interrupted(incident.id, "Daemon stopped during incident processing")
            raise
        except Exception:
            # Boundary: preserve a failure state instead of losing a background-task exception.
            self.logger.exception("Incident %s processing failed", incident.id)
            await self.fail_interrupted(incident.id, "Incident processing failed; see daemon logs")

    async def fail_interrupted(self, incident_id: UUID, reason: str) -> None:
        async with self.uow() as work:
            current = await work.repository.get(incident_id)
            if current and current.state not in {IncidentState.RESOLVED, IncidentState.FAILED}:
                await work.repository.interrupt_steps(incident_id, reason)
                await work.repository.transition(current, IncidentState.FAILED, reason)

    async def recover_interrupted(self) -> None:
        while True:
            async with self.uow() as work:
                incidents = await work.repository.list(active=True)
            if not incidents:
                return
            for incident in incidents:
                await self.fail_interrupted(incident.id, "Previous daemon stopped; remote command outcome may be unknown")

    async def stop(self) -> None:
        self.accepting = False
        if self.tasks:
            _, pending = await asyncio.wait(self.tasks, timeout=self.config.shutdown_timeout)
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)

    async def list(self, limit: int = 100) -> list[Incident]:
        async with self.uow() as work:
            return await work.repository.list(limit)

    async def detail(self, incident_id: UUID) -> IncidentDetail | None:
        async with self.uow() as work:
            return await work.repository.detail(incident_id)

    async def active_count(self) -> int:
        async with self.uow() as work:
            return await work.repository.active_count()
