"""Database schema owned by the ingest service.

Other services (e.g. the web API) read these tables but don't migrate them;
schema changes go through this service's Alembic migrations.
"""

from ..base import Base
from .article import Article, ArticleStatus
from .feed import FeedRecord

__all__ = ["Article", "ArticleStatus", "Base", "FeedRecord"]
