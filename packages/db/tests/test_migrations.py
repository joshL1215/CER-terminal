"""The Alembic migrations must build exactly the schema in src/cer_db/models/."""

import io
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from cer_db import Base, make_engine

ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"


def alembic_config(url: str) -> Config:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return config


def test_migrations_match_models_and_downgrade(database_url):
    engine = make_engine(database_url)
    Base.metadata.drop_all(engine)
    with engine.begin() as conn:
        conn.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")

    config = alembic_config(database_url)
    try:
        command.upgrade(config, "head")
        assert {"feeds", "articles"} <= set(inspect(engine).get_table_names())
        # Fails if the models have changes that no migration covers.
        command.check(config)

        command.downgrade(config, "base")
        assert not {"feeds", "articles"} & set(inspect(engine).get_table_names())
    finally:
        Base.metadata.drop_all(engine)
        with engine.begin() as conn:
            conn.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
        engine.dispose()


def test_migrated_database_accepts_rows(database_url):
    """Server defaults in the migrations must work on every backend, not just Postgres."""
    engine = make_engine(database_url)
    Base.metadata.drop_all(engine)
    config = alembic_config(database_url)
    try:
        command.upgrade(config, "head")
        with engine.begin() as conn:
            conn.exec_driver_sql(
                "insert into feeds (id, name, url, source_type, category, tags) "
                "values ('a', 'A', 'https://a.example.com', 'news', 'grid', '[]')"
            )
            conn.exec_driver_sql(
                "insert into articles (url_hash, url, feed_id, title) "
                "values ('h', 'https://a.example.com/1', 'a', 'T')"
            )
            feed = conn.exec_driver_sql("select active, created_at from feeds").one()
            article = conn.exec_driver_sql(
                "select status, fetched_at, classification_attempts from articles"
            ).one()
        assert bool(feed.active) is True and feed.created_at is not None
        assert article.status == "pending"
        assert article.fetched_at is not None
        assert article.classification_attempts == 0
    finally:
        command.downgrade(config, "base")
        with engine.begin() as conn:
            conn.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
        engine.dispose()


def test_offline_sql_generation():
    """`alembic upgrade --sql` must work without a database connection."""
    output = io.StringIO()
    config = Config(str(ALEMBIC_INI), output_buffer=output)
    config.set_main_option("sqlalchemy.url", "postgresql+psycopg://user@localhost/unused")
    command.upgrade(config, "head", sql=True)
    sql = output.getvalue()
    assert "create policy public_read_kept_articles" in sql
    assert "enable row level security" in sql
