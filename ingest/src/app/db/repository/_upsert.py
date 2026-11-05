from sqlalchemy import Insert
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.orm import Session


def upsert_insert(session: Session, model) -> Insert:
    """INSERT that supports ON CONFLICT, built for the session's database.

    Postgres runs in production and SQLite in tests; each has its own builder.
    """
    dialect = session.get_bind().dialect.name
    if dialect == "postgresql":
        return postgresql.insert(model)
    if dialect == "sqlite":
        return sqlite.insert(model)
    raise NotImplementedError(f"unsupported database dialect: {dialect}")
