"""What the public Supabase roles can and can't do after the RLS migration.

The fixture recreates Supabase's default privileges first (everything in
`public` granted to anon/authenticated), so the migration has to actively take
access away. Postgres only: SQLite has no roles or row-level security.
"""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from cer_db import Base, make_engine

ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"
PUBLIC_ROLES = ("anon", "authenticated")
SUPABASE_DEFAULTS = [
    "grant usage on schema public to anon, authenticated",
    "alter default privileges in schema public grant all on tables to anon, authenticated",
    "alter default privileges in schema public grant all on sequences to anon, authenticated",
    "alter default privileges in schema public grant all on functions to anon, authenticated",
]


@pytest.fixture
def pg_engine(database_url):
    if not database_url.startswith("postgresql"):
        pytest.skip("row-level security needs Postgres")

    engine = make_engine(database_url)
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))

    with engine.begin() as conn:
        existing = set(conn.scalars(text("select rolname from pg_roles")))
        created = [role for role in PUBLIC_ROLES if role not in existing]
        for role in created:
            conn.execute(text(f"create role {role} nologin"))
        for statement in SUPABASE_DEFAULTS:
            conn.execute(text(statement))
    Base.metadata.drop_all(engine)
    with engine.begin() as conn:
        conn.execute(text("drop table if exists alembic_version"))

    command.upgrade(config, "head")
    yield engine

    command.downgrade(config, "base")
    with engine.begin() as conn:
        conn.execute(text("drop table if exists alembic_version"))
        conn.execute(text("drop table if exists rls_probe"))
        for kind in ("tables", "sequences", "functions"):
            conn.execute(
                text(
                    f"alter default privileges in schema public "
                    f"revoke all on {kind} from anon, authenticated"
                )
            )
        conn.execute(text("revoke usage on schema public from anon, authenticated"))
        for role in created:
            conn.execute(text(f"drop role {role}"))
    engine.dispose()


@pytest.fixture
def seeded(pg_engine):
    with pg_engine.begin() as conn:
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
                "('h4', 'https://on.example.com/4', 'on', 'Failed', 'failed'), "
                "('h5', 'https://off.example.com/5', 'off', 'Kept, inactive feed', 'kept')"
            )
        )
    return pg_engine


def run_as(engine, role: str, sql: str):
    with engine.connect() as conn:
        conn.execute(text(f"set role {role}"))
        try:
            return conn.execute(text(sql)).all()
        finally:
            conn.rollback()


@pytest.mark.parametrize("role", PUBLIC_ROLES)
def test_reads_only_kept_articles_from_active_feeds(seeded, role):
    rows = run_as(seeded, role, "select title from articles")
    assert [row.title for row in rows] == ["Kept"]


@pytest.mark.parametrize("role", PUBLIC_ROLES)
def test_reads_only_active_feeds(seeded, role):
    rows = run_as(seeded, role, "select id from feeds")
    assert [row.id for row in rows] == ["on"]


@pytest.mark.parametrize("role", PUBLIC_ROLES)
@pytest.mark.parametrize(
    "sql",
    [
        "select reason from articles",
        "select status from articles",
        "select * from articles",
        "select last_error from feeds",
        "select llm_context from feeds",
    ],
)
def test_internal_columns_hidden(seeded, role, sql):
    with pytest.raises(ProgrammingError, match="permission denied"):
        run_as(seeded, role, sql)


@pytest.mark.parametrize("role", PUBLIC_ROLES)
@pytest.mark.parametrize(
    "sql",
    [
        "insert into articles (url_hash, url, feed_id, title) values ('x', 'u', 'on', 't')",
        "update articles set title = 'hacked'",
        "delete from articles",
        "truncate articles",
        "delete from feeds",
        "truncate feeds",
        "select * from alembic_version",
        "update alembic_version set version_num = 'x'",
        "delete from alembic_version",
        "select nextval('articles_id_seq')",
    ],
)
def test_writes_and_internal_tables_denied(seeded, role, sql):
    with pytest.raises(ProgrammingError, match="permission denied"):
        run_as(seeded, role, sql)


@pytest.mark.parametrize("role", PUBLIC_ROLES)
def test_exact_table_privileges(pg_engine, role):
    with pg_engine.connect() as conn:
        grants = conn.execute(
            text(
                "select table_name, privilege_type from information_schema.role_table_grants "
                "where grantee = :role and table_schema = 'public'"
            ),
            {"role": role},
        ).all()
        columns = conn.execute(
            text(
                "select table_name, column_name from information_schema.column_privileges "
                "where grantee = :role and table_schema = 'public' and privilege_type = 'SELECT'"
            ),
            {"role": role},
        ).all()
    assert grants == []  # no table-wide privileges at all
    assert {(row.table_name, row.column_name) for row in columns} == {
        ("articles", c)
        for c in ("id", "url", "title", "description", "published_at", "category", "feed_id")
    } | {("feeds", c) for c in ("id", "name", "url", "category", "tags")}


@pytest.mark.parametrize("role", PUBLIC_ROLES)
def test_new_tables_are_not_exposed(pg_engine, role):
    with pg_engine.begin() as conn:
        conn.execute(text("create table rls_probe (id int)"))
    with pytest.raises(ProgrammingError, match="permission denied"):
        run_as(pg_engine, role, "select * from rls_probe")


def test_owner_still_sees_everything(seeded):
    with seeded.connect() as conn:
        assert conn.scalar(text("select count(*) from articles")) == 5
        assert conn.scalar(text("select count(*) from feeds")) == 2
