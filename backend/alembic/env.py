"""Alembic environment script.

Configures Alembic to:
- read the database URL from our own validated settings (infrastructure
  .config.settings, which in turn reads the DATABASE_URL environment
  variable) instead of a hardcoded connection string in alembic.ini, and
- use infrastructure.db.base.Base's metadata as the source of truth for
  "what tables/columns should exist", by importing infrastructure.db.models
  so every table class gets registered on that metadata before Alembic
  looks at it.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Import the app's own settings and models so Alembic uses the exact same
# database URL and table definitions as the running application.
from infrastructure.config import settings
from infrastructure.db.base import Base
from infrastructure.db import models  # noqa: F401  (registers User/Expense on Base.metadata)

# this is the Alembic Config object, which provides access to values within
# the .ini file in use.
config = context.config

# Override whatever is (or isn't) in alembic.ini's sqlalchemy.url with the
# real, validated DATABASE_URL from our settings.
config.set_main_option("sqlalchemy.url", settings.database_url)

# Interpret the config file for Python logging, unless we were invoked
# without a config file (e.g. some test setups).
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generates SQL without a live DB
    connection - not used in our normal workflow, but kept for completeness
    since it's part of Alembic's standard template)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode, connecting to the real database."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
