"""Queries the ingest job uses. Each function takes a Session; callers own the transaction."""

from .articles import (
    Classification,
    NewArticle,
    count_pending_articles,
    get_pending_articles,
    insert_new_articles,
    record_classification_failure,
    record_classifications,
)
from .feeds import get_feed, record_fetch_failure, record_fetch_success, sync_feeds

__all__ = [
    "Classification",
    "NewArticle",
    "count_pending_articles",
    "get_feed",
    "get_pending_articles",
    "insert_new_articles",
    "record_classification_failure",
    "record_classifications",
    "record_fetch_failure",
    "record_fetch_success",
    "sync_feeds",
]
