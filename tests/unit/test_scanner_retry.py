import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from yubarta.config.settings import LogWatch
from yubarta.controllers.scanners.base import BaseScanner


async def test_repeated_short_sessions_use_bounded_exponential_backoff() -> None:
    scanner = BaseScanner(LogWatch(name="retry", file="/tmp/log", reconnect_initial=1, reconnect_max=4), "host", AsyncMock())

    async def end_session() -> None:
        scanner.connected()

    scanner.run_session = end_session
    with patch("yubarta.controllers.scanners.base.asyncio.sleep", new_callable=AsyncMock) as sleep:
        sleep.side_effect = [None, None, None, asyncio.CancelledError()]
        with pytest.raises(asyncio.CancelledError):
            await scanner.run()
    assert [call.args[0] for call in sleep.await_args_list] == [1, 2, 4, 4]
    assert scanner.status.reconnect_count == 4
