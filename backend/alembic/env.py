import asyncio
from logging.config import fileConfig
import os
import sys
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

from alembic import context

# Add the parent directory to the path so we can import our app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

# Import our models
from app.core.database import Base
from app.models.models import *  # noqa

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the database URL from centralized settings
from app.core.config import settings
database_url = settings.DATABASE_URL
# Ensure we use the async driver for Postgres
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
config.set_main_option("sqlalchemy.url", database_url)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

_MIGRATION_LOCK_KEY = 81420260805

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    is_postgresql = connection.dialect.name == "postgresql"
    if is_postgresql:
        # Session-level locking must precede configure/run_migrations so two
        # Alembic processes cannot compute and apply the same revision plan.
        connection.execute(text(f"SELECT pg_advisory_lock({_MIGRATION_LOCK_KEY})"))
        # End SQLAlchemy's implicit transaction. Session advisory locks survive
        # commit, allowing Alembic to open its own migration transaction.
        connection.commit()
    try:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()
    finally:
        if is_postgresql:
            connection.execute(text(f"SELECT pg_advisory_unlock({_MIGRATION_LOCK_KEY})"))


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    
    # create_async_engine requires the URL to be suitable for an async driver
    url = config.get_main_option("sqlalchemy.url")
    connectable = create_async_engine(
        url,
        poolclass=pool.NullPool,
    )

    try:
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
