from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool

from app.db.engine import make_engine
from app.db.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def _database_url() -> str | None:
    # An explicit URL (e.g. set by tests) wins; otherwise make_engine reads DATABASE_URL.
    return config.get_main_option("sqlalchemy.url") or None


def run_migrations_offline() -> None:
    """Emit SQL to stdout instead of running it: `alembic upgrade head --sql`."""
    context.configure(
        url=make_engine(_database_url()).url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = make_engine(_database_url(), poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=connection.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
