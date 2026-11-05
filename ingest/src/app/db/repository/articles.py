"""Article queries: storing new items and recording relevance decisions."""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.urls import url_hash

from ..models import Article, ArticleStatus
from ._upsert import upsert_insert


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
        upsert_insert(session, Article)
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
    at = at or datetime.now(UTC)
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
