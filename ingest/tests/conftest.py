"""Database fixtures.

Tests run against SQLite by default. Set TEST_DATABASE_URL to a disposable
Postgres database to run them against Postgres too (tables are dropped!).
"""

import os

import pytest

from app.db import Base, make_engine, make_session_factory

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
BACKENDS = ["sqlite"] + (["postgresql"] if TEST_DATABASE_URL else [])


def _url_for(backend: str, tmp_path) -> str:
    if backend == "sqlite":
        return f"sqlite:///{tmp_path / 'test.db'}"
    url = TEST_DATABASE_URL
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            url = "postgresql+psycopg://" + url.removeprefix(prefix)
    return url


@pytest.fixture(params=BACKENDS)
def database_url(request, tmp_path) -> str:
    return _url_for(request.param, tmp_path)


@pytest.fixture
def engine(database_url):
    engine = make_engine(database_url)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def session(engine):
    factory = make_session_factory(engine)
    with factory() as session:
        yield session
        session.rollback()
