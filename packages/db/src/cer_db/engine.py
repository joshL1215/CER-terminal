"""Engine and session setup."""

import os
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker


class DatabaseConfigError(RuntimeError):
    """Raised when DATABASE_URL is missing."""


def database_url_from_env() -> str:
    """Read DATABASE_URL, pointing plain postgres URLs at the psycopg 3 driver.

    Supabase and most hosts hand out `postgresql://` or `postgres://` URLs,
    which SQLAlchemy would otherwise map to psycopg2.
    """
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise DatabaseConfigError("DATABASE_URL is not set")
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url.removeprefix(prefix)
    return url


def make_engine(url: str | None = None, **kwargs) -> Engine:
    url = url or database_url_from_env()
    if url.startswith("postgresql+psycopg"):
        # Disable server-side prepared statements so this also works through
        # PgBouncer/Supavisor transaction-mode poolers.
        kwargs.setdefault("connect_args", {}).setdefault("prepare_threshold", None)
        kwargs.setdefault("pool_pre_ping", True)
    engine = create_engine(url, **kwargs)
    if engine.dialect.name == "sqlite":
        # SQLite ignores foreign keys unless asked; keep tests honest.
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    return engine


def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    """Yield a session that commits on success and rolls back on error."""
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
