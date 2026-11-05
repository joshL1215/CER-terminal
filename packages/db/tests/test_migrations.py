"""The Alembic migrations must build exactly the schema in src/cer_db/models/."""

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
