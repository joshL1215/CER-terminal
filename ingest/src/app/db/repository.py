"""Queries the ingest job uses. Each function takes a Session; callers own the transaction.

Typical run:

    with session_scope(factory) as session:
        sync_feeds(session, registry)
    for feed in registry.active():
        ...fetch...
        with session_scope(factory) as session:
            insert_new_articles(session, items)
            record_fetch_success(session, feed.id, etag=..., last_modified=...)
    with session_scope(factory) as session:
        pending = get_pending_articles(session, limit=50)
        ...classify...
        record_classifications(session, results)
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import Insert, func, select, update
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.orm import Session

from app.feeds import FeedRegistry
from app.urls import url_hash

from .models import Article, ArticleStatus, FeedRecord

MAX_ERROR_LENGTH = 2000


@dataclass(frozen=True)
class NewArticle:
    """A parsed feed item, before it's stored."""

    feed_id: str
    url: str
    title: str
    description: str | None = None
    published_at: datetime | None = None


@dataclass(frozen=True)
class Classification:
    """The relevance decision for one stored article."""

    article_id: int
    status: ArticleStatus  # KEPT or REJECTED
    category: str | None = None
    reason: str | None = None
    model: str | None = None
    rules_version: str | None = None


def _now() -> datetime:
    return datetime.now(UTC)


def _insert(session: Session, model) -> Insert:
    """Dialect-specific INSERT that supports ON CONFLICT (Postgres in prod, SQLite in tests)."""
    dialect = session.get_bind().dialect.name
    if dialect == "postgresql":
        return postgresql.insert(model)
    if dialect == "sqlite":
        return sqlite.insert(model)
    raise NotImplementedError(f"unsupported database dialect: {dialect}")


# --- feeds -------------------------------------------------------------------


def sync_feeds(session: Session, registry: FeedRegistry) -> None:
    """Mirror feeds.yaml into the feeds table.

    Inserts new feeds, updates metadata on existing ones, and marks feeds that
    were removed from the YAML as inactive (kept, since articles reference them).
    Fetch state (etag, failures, ...) is left untouched.
    """
    rows = [
        {
            "id": feed.id,
            "name": feed.name,
            "url": feed.url,
            "source_type": feed.source_type.value,
            "category": feed.category,
            "tags": list(feed.tags),
            "active": feed.active,
            "llm_context": feed.llm_context,
        }
        for feed in registry.feeds
    ]
    stmt = _insert(session, FeedRecord).values(rows)
    metadata_columns = ("name", "url", "source_type", "category", "tags", "active", "llm_context")
    stmt = stmt.on_conflict_do_update(
        index_elements=[FeedRecord.id],
        set_={column: stmt.excluded[column] for column in metadata_columns}
        | {"updated_at": _now()},
    )
    session.execute(stmt)

    yaml_ids = [feed.id for feed in registry.feeds]
    session.execute(
        update(FeedRecord)
        .where(FeedRecord.id.not_in(yaml_ids), FeedRecord.active.is_(True))
        .values(active=False, updated_at=_now())
    )


def get_feed(session: Session, feed_id: str) -> FeedRecord | None:
    return session.get(FeedRecord, feed_id)


def record_fetch_success(
    session: Session,
    feed_id: str,
    *,
    etag: str | None = None,
    last_modified: str | None = None,
    at: datetime | None = None,
) -> None:
    """Store conditional-GET headers and reset the failure counter.

    Call this for 304 Not Modified responses too; pass the existing etag and
    last_modified through if the server didn't send new ones.
    """
    at = at or _now()
    session.execute(
        update(FeedRecord)
        .where(FeedRecord.id == feed_id)
        .values(
            etag=etag,
            last_modified=last_modified,
            last_fetched_at=at,
            last_success_at=at,
            consecutive_failures=0,
            last_error=None,
        )
    )


def record_fetch_failure(
    session: Session, feed_id: str, error: str, *, at: datetime | None = None
) -> None:
    session.execute(
        update(FeedRecord)
        .where(FeedRecord.id == feed_id)
        .values(
            last_fetched_at=at or _now(),
            consecutive_failures=FeedRecord.consecutive_failures + 1,
            last_error=error[:MAX_ERROR_LENGTH],
        )
    )


# --- articles ----------------------------------------------------------------


def insert_new_articles(session: Session, items: Iterable[NewArticle]) -> int:
    """Store items not seen before (by canonical URL); returns how many were new."""
    rows: dict[str, dict] = {}
    for item in items:
        key = url_hash(item.url)
        # First occurrence wins if the same article appears twice in one batch.
        rows.setdefault(
            key,
            {
                "url_hash": key,
                "url": item.url.strip(),
                "feed_id": item.feed_id,
                "title": item.title.strip(),
                "description": item.description,
                "published_at": item.published_at,
            },
        )
    if not rows:
        return 0

    stmt = (
        _insert(session, Article)
        .values(list(rows.values()))
        .on_conflict_do_nothing(index_elements=[Article.url_hash])
        .returning(Article.id)
    )
    return len(session.execute(stmt).all())


def get_pending_articles(session: Session, *, limit: int = 50) -> Sequence[Article]:
    """Oldest articles still waiting for a relevance decision."""
    return session.scalars(
        select(Article)
        .where(Article.status == ArticleStatus.PENDING)
        .order_by(Article.fetched_at, Article.id)
        .limit(limit)
    ).all()


def count_pending_articles(session: Session) -> int:
    return session.scalar(
        select(func.count()).select_from(Article).where(Article.status == ArticleStatus.PENDING)
    )


def record_classifications(
    session: Session, results: Iterable[Classification], *, at: datetime | None = None
) -> None:
    at = at or _now()
    for result in results:
        if result.status not in (ArticleStatus.KEPT, ArticleStatus.REJECTED):
            raise ValueError(f"classification status must be kept or rejected, not {result.status}")
        session.execute(
            update(Article)
            .where(Article.id == result.article_id)
            .values(
                status=result.status,
                category=result.category,
                reason=result.reason,
                model=result.model,
                rules_version=result.rules_version,
                classified_at=at,
                classification_attempts=Article.classification_attempts + 1,
            )
        )


def record_classification_failure(
    session: Session, article_ids: Iterable[int], *, max_attempts: int = 3
) -> None:
    """Count a failed LLM attempt; articles that hit max_attempts become FAILED."""
    ids = list(article_ids)
    if not ids:
        return
    session.execute(
        update(Article)
        .where(Article.id.in_(ids), Article.status == ArticleStatus.PENDING)
        .values(classification_attempts=Article.classification_attempts + 1)
    )
    session.execute(
        update(Article)
        .where(
            Article.id.in_(ids),
            Article.status == ArticleStatus.PENDING,
            Article.classification_attempts >= max_attempts,
        )
        .values(status=ArticleStatus.FAILED)
    )
