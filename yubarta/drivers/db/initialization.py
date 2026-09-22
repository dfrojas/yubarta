import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config


def migrate_sync(url: str) -> None:
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).parent / "migrations"))
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.upgrade(config, "head")


async def migrate(url: str) -> None:
    await asyncio.to_thread(migrate_sync, url)
