"""The public (anon) role can read kept articles and active feeds, and nothing else.

Postgres only: SQLite has no roles or row-level security.
"""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from cer_db import Base, make_engine

ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"
SUPABASE_ROLES = ("anon", "authenticated")


@pytest.fixture
def pg_engine(database_url):
    if not database_url.startswith("postgresql"):
        pytest.skip("row-level security needs Postgres")

    engine = make_engine(database_url)
    with engine.begin() as conn:
        existing = set(
            conn.scalars(
                text("select rolname from pg_roles where rolname in ('anon', 'authenticated')")
            )
        )
        created = [role for role in SUPABASE_ROLES if role not in existing]
        for role in created:
            conn.execute(text(f"create role {role} nologin"))

    config = Config(str(ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    Base.metadata.drop_all(engine)
    with engine.begin() as conn:
        conn.execute(text("drop table if exists alembic_version"))
    command.upgrade(config, "head")

    yield engine

    command.downgrade(config, "base")
    with engine.begin() as conn:
        conn.execute(text("drop table if exists alembic_version"))
        for role in created:
            conn.execute(text(f"drop role {role}"))
    engine.dispose()


def seed(conn) -> None:
    conn.execute(
        text(
            "insert into feeds (id, name, url, source_type, category, tags, active) values "
            "('on', 'On', 'https://on.example.com', 'news', 'grid', '[]', true), "
            "('off', 'Off', 'https://off.example.com', 'news', 'grid', '[]', false)"
        )
    )
    conn.execute(
        text(
            "insert into articles (url_hash, url, feed_id, title, status) values "
            "('h1', 'https://on.example.com/1', 'on', 'Kept', 'kept'), "
            "('h2', 'https://on.example.com/2', 'on', 'Rejected', 'rejected'), "
            "('h3', 'https://on.example.com/3', 'on', 'Pending', 'pending'), "
            "('h4', 'https://on.example.com/4', 'on', 'Failed', 'failed')"
        )
    )


def test_anon_reads_only_kept_articles_and_active_feeds(pg_engine):
    with pg_engine.begin() as conn:
        seed(conn)

    with pg_engine.connect() as conn:
        conn.execute(text("set role anon"))
        assert conn.scalars(text("select title from articles")).all() == ["Kept"]
        assert conn.scalars(text("select id from feeds")).all() == ["on"]
        conn.rollback()


@pytest.mark.parametrize(
    "statement",
    [
        "insert into articles (url_hash, url, feed_id, title) values ('x', 'u', 'on', 't')",
        "update articles set title = 'hacked'",
        "delete from feeds",
    ],
)
def test_anon_cannot_write(pg_engine, statement):
    with pg_engine.begin() as conn:
        seed(conn)

    with pg_engine.connect() as conn:
        conn.execute(text("set role anon"))
        with pytest.raises(ProgrammingError, match="permission denied"):
            conn.execute(text(statement))
        conn.rollback()


def test_owner_still_sees_everything(pg_engine):
    with pg_engine.begin() as conn:
        seed(conn)
        assert conn.scalar(text("select count(*) from articles")) == 4
