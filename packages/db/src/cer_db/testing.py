"""Pytest fixtures for any service's database tests.

Enable in a conftest.py with `pytest_plugins = ["cer_db.testing"]`.

Tests run against SQLite by default. Set TEST_DATABASE_URL to a disposable
Postgres database to run them against Postgres too (tables are dropped!).
"""

import os

import pytest

from .base import Base
from .engine import make_engine, make_session_factory

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
BACKENDS = ["sqlite"] + (["postgresql"] if TEST_DATABASE_URL else [])


@pytest.fixture(params=BACKENDS)
def database_url(request, tmp_path) -> str:
    if request.param == "sqlite":
        return f"sqlite:///{tmp_path / 'test.db'}"
    url = TEST_DATABASE_URL
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            url = "postgresql+psycopg://" + url.removeprefix(prefix)
    return url


@pytest.fixture
def engine(database_url):
    """An engine on an empty database with all tables created."""
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
