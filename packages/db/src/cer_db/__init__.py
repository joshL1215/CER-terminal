"""Shared database layer: table definitions and connection setup.

Every service that touches the database imports its tables from here, so
there is one definition of the schema. Migrations for it live in this package.
"""

from .base import Base
from .engine import (
    DatabaseConfigError,
    database_url_from_env,
    make_engine,
    make_session_factory,
    session_scope,
)
from .models import Article, ArticleStatus, FeedRecord

__all__ = [
    "Article",
    "ArticleStatus",
    "Base",
    "DatabaseConfigError",
    "FeedRecord",
    "database_url_from_env",
    "make_engine",
    "make_session_factory",
    "session_scope",
]
