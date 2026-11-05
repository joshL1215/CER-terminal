import pytest
from sqlalchemy import select

from cer_db import (
    DatabaseConfigError,
    FeedRecord,
    database_url_from_env,
    make_session_factory,
    session_scope,
)


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


def make_feed(feed_id: str) -> FeedRecord:
    return FeedRecord(
        id=feed_id,
        name=feed_id.title(),
        url=f"https://{feed_id}.example.com/rss",
        source_type="news",
        category="general",
        tags=[],
    )


def test_session_scope_commits_and_rolls_back(engine):
    factory = make_session_factory(engine)

    with pytest.raises(RuntimeError), session_scope(factory) as session:
        session.add(make_feed("alpha"))
        session.flush()
        raise RuntimeError("boom")
    with factory() as session:
        assert session.scalars(select(FeedRecord)).all() == []

    with session_scope(factory) as session:
        session.add_all([make_feed("alpha"), make_feed("beta")])
    with factory() as session:
        assert len(session.scalars(select(FeedRecord)).all()) == 2
