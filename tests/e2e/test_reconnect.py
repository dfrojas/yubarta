import asyncio

import pytest

from tests.support import Daemon
from yubarta.drivers.network.ssh import SSH

pytestmark = pytest.mark.e2e


async def test_disconnect_backfill_dedup_and_future_incident(daemon: Daemon, ssh: SSH) -> None:
    assert (await ssh.run("sudo -n sandbox-control disconnect-scanners", 5)).passed
    await daemon.wait_scanner("reconnecting", 1)
    # A fresh execution session works while the scanner session is disconnected.
    assert (await ssh.run("sudo -n sandbox-control fail", 5)).passed
    await daemon.wait_scanner("connected", 1)
    detail = await daemon.wait_incident("RESOLVED")
    assert len(detail["events"]) == 1
    assert len(await daemon.get("/incidents")) == 1
    assert (await ssh.run("sudo -n sandbox-control disconnect-scanners", 5)).passed
    await daemon.wait_scanner("connected", 2)
    await asyncio.sleep(0.5)
    assert len(await daemon.get("/incidents")) == 1
    assert len((await daemon.get(f"/incidents/{detail['id']}"))["events"]) == 1
    assert (await ssh.run("sudo -n sandbox-control fail", 5)).passed
    future = await daemon.wait_incident("RESOLVED", count=2)
    assert future["id"] != detail["id"]
