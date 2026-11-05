import pytest
from sqlalchemy import select

from app.db import (
    DatabaseConfigError,
    FeedRecord,
    database_url_from_env,
    session_scope,
    sync_feeds,
)
from app.db.engine import make_session_factory


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("postgres://u:p@h:5432/db", "postgresql+psycopg://u:p@h:5432/db"),
        ("postgresql://u:p@h:5432/db", "postgresql+psycopg://u:p@h:5432/db"),
        ("postgresql+psycopg://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("sqlite:///local.db", "sqlite:///local.db"),
    ],
)
def test_database_url_from_env(monkeypatch, raw, expected):
    monkeypatch.setenv("DATABASE_URL", raw)
    assert database_url_from_env() == expected


def test_database_url_missing(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(DatabaseConfigError):
        database_url_from_env()


def test_session_scope_commits_and_rolls_back(engine, registry):
    factory = make_session_factory(engine)

    with pytest.raises(RuntimeError), session_scope(factory) as session:
        sync_feeds(session, registry)
        raise RuntimeError("boom")
    with factory() as session:
        assert session.scalars(select(FeedRecord)).all() == []

    with session_scope(factory) as session:
        sync_feeds(session, registry)
    with factory() as session:
        assert len(session.scalars(select(FeedRecord)).all()) == 2
