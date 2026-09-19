"""SSH fixtures: in-process fake target."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from tests.integration.fake_ssh import FakeTargetState, close_fake_ssh_server, start_fake_ssh_server


@pytest.fixture()
async def ssh_target() -> AsyncIterator[tuple[FakeTargetState, int]]:
    state = FakeTargetState(healthy=True)
    state.log_lines.extend(["line one", "line two"])
    listener, port = await start_fake_ssh_server(state)
    try:
        yield state, port
    finally:
        await close_fake_ssh_server(listener, state)
