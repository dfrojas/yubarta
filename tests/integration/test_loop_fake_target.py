"""Integration: remediation loop assembled against an in-process SSH target."""

from __future__ import annotations

import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from tests.integration.fake_ssh import FakeTargetState, start_fake_ssh_server
from yubarta.config import (
    AppConfig,
    CommandCheck,
    HttpCheck,
    LogWatch,
    RemediationDef,
    TargetConfig,
    VerifyConfig,
)
from yubarta.diagnostics.runner import DiagnosticsRunner
from yubarta.execution.ssh import AsyncSSHExecutor
from yubarta.incidents.service import IncidentService
from yubarta.persistence.repository import IncidentRepository
from yubarta.persistence.session import create_engine, create_session_factory, init_db
from yubarta.rules.engine import RuleEngine
from yubarta.scanners.remote_file import RemoteFileScanner


def _health_server(state: FakeTargetState) -> HTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            body = b"OK" if state.healthy else b"down"
            self.send_response(200 if state.healthy else 503)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):  # noqa: ANN002, ANN202
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


async def test_remediation_loop_fake_target(test_db: str) -> None:
    state = FakeTargetState(healthy=True)
    listener, ssh_port = await start_fake_ssh_server(state)
    http_server = _health_server(state)
    http_url = f"http://127.0.0.1:{http_server.server_port}/health"
    try:
        url = test_db
        engine = create_engine(url)
        await init_db(engine)
        sessions = create_session_factory(engine)
        config = AppConfig(
            target=TargetConfig(host="127.0.0.1", user="tester", key="", port=ssh_port),
            watch=[
                LogWatch(
                    file="/var/log/apache2/error.log",
                    match_any=["AH00957", "AJP", "Connection refused"],
                )
            ],
            diagnostics=["uptime", "free -h"],
            checks=[
                CommandCheck(
                    run="sudo -n systemctl is-active --quiet tomcat9",
                    expect_exit_code=0,
                ),
                HttpCheck(http=http_url, expect_status=200),
            ],
            remediations=[
                RemediationDef(name="ensure-swap", command="ensure-swap"),
                RemediationDef(name="fix-restart-policy", command="fix-restart-policy"),
                RemediationDef(name="restart-tomcat", command="sudo -n systemctl restart tomcat9"),
            ],
            verify=VerifyConfig(settle_delay=0.0, interval=0.1, timeout=10.0),
        )
        executor = AsyncSSHExecutor(config.target)
        service = IncidentService(
            config,
            sessions,
            RuleEngine.from_watches(config.watch),
            executor,
            DiagnosticsRunner(executor, config.diagnostics),
            apply=True,
        )

        # 1-2: healthy at start
        assert state.healthy is True

        scanner = RemoteFileScanner(name="e2e-log", target=config.target, watch=config.watch[0])  # type: ignore[arg-type]
        await scanner.start(service.handle_event)
        try:
            # 3-5: inject failure + Apache-like log
            state.healthy = False
            await asyncio.sleep(0.2)
            state.append_log("[proxy_ajp:error] AH00957: AJP: Connection refused to 127.0.0.1:8009 (tomcat)")
            # 6-18: wait for full loop to resolve
            incident_id: str | None = None
            final_state = ""
            for _ in range(400):
                async with sessions() as session:
                    repo = IncidentRepository(session)
                    incidents = await repo.list_incidents()
                    if incidents:
                        incident_id = incidents[0].id
                        final_state = incidents[0].state
                        if final_state == "RESOLVED":
                            break
                await asyncio.sleep(0.1)
            assert incident_id is not None, "incident was never created"
            assert final_state == "RESOLVED", f"incident did not resolve: {final_state}"

            # 19: attribution to restart-tomcat
            async with sessions() as session:
                repo = IncidentRepository(session)
                row = await repo.get(incident_id)
                assert row is not None and row.resolved_by_step_id
                steps = await repo.list_steps(incident_id)
                by_id = {step.id: step for step in steps}
                assert by_id[row.resolved_by_step_id].name == "restart-tomcat"
                kinds = [step.kind for step in steps]
                assert "diagnostic" in kinds and "remediation" in kinds and "verification" in kinds
                # 20: timeline queryable
                transitions = await repo.list_transitions(incident_id)
                assert len(transitions) >= 5
                # earlier remediations preserved even though they did not fix it
                remediation_names = [step.name for step in steps if step.kind == "remediation"]
                assert remediation_names == [
                    "ensure-swap",
                    "fix-restart-policy",
                    "restart-tomcat",
                ]
        finally:
            await scanner.stop()
        await engine.dispose()
    finally:
        listener.close()
        await listener.wait_closed()
        http_server.shutdown()
