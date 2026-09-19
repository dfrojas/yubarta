"""Integration target: real SSH wire protocol with an in-process fake shell."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field

import asyncssh


@dataclass
class FakeTargetState:
    healthy: bool = True
    log_lines: list[str] = field(default_factory=list)
    command_routes: dict[str, tuple[int, str]] = field(default_factory=dict)
    _subscribers: list[asyncio.Queue[str]] = field(default_factory=list, repr=False)
    _processes: list = field(default_factory=list, repr=False)

    def append_log(self, line: str) -> None:
        self.log_lines.append(line)
        for queue in list(self._subscribers):
            queue.put_nowait(line)

    def route(self, command: str, exit_code: int, stdout: str = "") -> None:
        self.command_routes[command.strip()] = (exit_code, stdout)


def _default_routing(state: FakeTargetState, command: str) -> tuple[int, str, str]:
    cmd = command.strip()
    if cmd in state.command_routes:
        code, out = state.command_routes[cmd]
        return code, out, ""
    if "is-active" in cmd and "tomcat" in cmd:
        return (0, "", "") if state.healthy else (3, "inactive\n", "")
    if "is-failed" in cmd and "tomcat" in cmd:
        return (0, "active\n", "") if state.healthy else (0, "failed\n", "")
    if cmd.startswith("sudo -n systemctl restart") or cmd == "restart-tomcat":
        state.healthy = True
        return 0, "", ""
    if cmd in ("ensure-swap", "/opt/yubarta/ensure-swap"):
        return 0, "swap ensured\n", ""
    if cmd in ("fix-restart-policy", "/opt/yubarta/fix-tomcat-restart-policy"):
        return 0, "restart policy ensured\n", ""
    # diagnostics default: success with echo
    return 0, f"output of: {cmd}\n", ""


class _AllowServer(asyncssh.SSHServer):
    def begin_auth(self, username: str) -> bool:
        return False

    def password_auth_supported(self) -> bool:
        return True

    def publickey_auth_supported(self) -> bool:
        return True


def make_process_handler(state: FakeTargetState):  # type: ignore[no-untyped-def]
    async def handle(process: asyncssh.SSHServerProcess) -> None:
        state._processes.append(process)
        command = (process.command or "").strip()
        try:
            await _serve(process, state, command)
        finally:
            if process in state._processes:
                state._processes.remove(process)

    async def _serve(process: asyncssh.SSHServerProcess, state: FakeTargetState, command: str) -> None:
        tail_match = re.match(r"tail\s+-n\s+(\d+)\s+(-F\s+)?(\S+)", command)
        if tail_match:
            count = int(tail_match.group(1))
            follow = tail_match.group(2) is not None
            lines = state.log_lines[-count:] if count else []
            for line in lines:
                try:
                    process.stdout.write(line + "\n")
                except (BrokenPipeError, asyncssh.BrokenChannelError, ValueError):
                    return
            if not follow:
                process.exit(0)
                return
            queue: asyncio.Queue[str] = asyncio.Queue()
            state._subscribers.append(queue)
            try:
                while True:
                    try:
                        line = await asyncio.wait_for(queue.get(), timeout=30.0)
                    except TimeoutError:
                        if process.is_closing():
                            return
                        continue
                    try:
                        process.stdout.write(line + "\n")
                    except (BrokenPipeError, asyncssh.BrokenChannelError, ValueError):
                        return
                    if process.is_closing():
                        return
            except asyncio.CancelledError:
                return
            finally:
                if queue in state._subscribers:
                    state._subscribers.remove(queue)
            return
        code, out, err = _default_routing(state, command)
        if out:
            try:
                process.stdout.write(out)
            except (BrokenPipeError, asyncssh.BrokenChannelError, ValueError):
                return
        if err:
            try:
                process.stderr.write(err)
            except (BrokenPipeError, asyncssh.BrokenChannelError, ValueError):
                pass
        process.exit(code)

    return handle


async def start_fake_ssh_server(state: FakeTargetState, port: int = 0):  # type: ignore[no-untyped-def]
    host_key = asyncssh.generate_private_key("ssh-rsa")
    listener = await asyncssh.create_server(
        _AllowServer,
        "127.0.0.1",
        port,
        server_host_keys=[host_key],
        process_factory=make_process_handler(state),
    )
    bound_port = listener.get_port()
    return listener, bound_port


def disconnect_all(state: FakeTargetState) -> None:
    """Abort all established server-side channels, simulating a dropped connection."""
    for process in list(state._processes):
        try:
            process.channel.abort()
        except Exception:
            pass
