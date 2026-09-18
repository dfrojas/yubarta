"""Alembic environment: autogenerate from yubarta.persistence.models.Base."""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from yubarta.persistence.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    url = os.environ.get("YUBARTA_DATABASE_URL", "postgresql+psycopg://yubarta:yubarta@localhost/yubarta")
    # Alembic runs sync: convert async drivers to sync ones.
    return url.replace("postgresql+asyncpg", "postgresql+psycopg").replace("sqlite+aiosqlite", "sqlite")


def run_migrations_offline() -> None:
    context.configure(url=get_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(get_url())
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
