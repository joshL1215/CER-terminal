from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db import (
    Article,
    ArticleStatus,
    Classification,
    NewArticle,
    count_pending_articles,
    get_pending_articles,
    insert_new_articles,
    record_classification_failure,
    record_classifications,
)


def article(n: int, feed_id: str = "alpha", **kwargs) -> NewArticle:
    return NewArticle(
        feed_id=feed_id, url=f"https://alpha.example.com/story-{n}", title=f"Story {n}", **kwargs
    )


def test_insert_new_articles_dedupes_within_batch_and_across_runs(session, feeds):
    first = [
        article(1),
        article(2),
        NewArticle(
            feed_id="alpha", url="https://alpha.example.com/story-1/?utm_source=rss", title="Dup"
        ),
    ]
    assert insert_new_articles(session, first) == 2
    session.commit()

    # Same story via another feed, plus one new one.
    second = [article(2, feed_id="beta"), article(3, feed_id="beta")]
    assert insert_new_articles(session, second) == 1
    session.commit()

    rows = session.scalars(select(Article).order_by(Article.id)).all()
    assert [row.title for row in rows] == ["Story 1", "Story 2", "Story 3"]
    assert rows[1].feed_id == "alpha"  # first feed to see it keeps it
    assert all(row.status is ArticleStatus.PENDING for row in rows)
    assert all(row.classification_attempts == 0 for row in rows)


def test_insert_new_articles_empty(session, feeds):
    assert insert_new_articles(session, []) == 0


def test_insert_article_for_unknown_feed_fails(session, feeds):
    with pytest.raises(IntegrityError):
        insert_new_articles(session, [article(1, feed_id="nope")])
        session.flush()


def test_article_fields_round_trip(session, feeds):
    published = datetime(2026, 11, 3, 14, 30, tzinfo=UTC)
    insert_new_articles(session, [article(1, description="Desc", published_at=published)])
    session.commit()
    row = session.scalars(select(Article)).one()
    assert row.description == "Desc"
    assert row.published_at.replace(tzinfo=row.published_at.tzinfo or UTC) == published
    assert row.url_hash and len(row.url_hash) == 64
    assert row.fetched_at is not None


def test_pending_articles_oldest_first_with_limit(session, feeds):
    insert_new_articles(session, [article(n) for n in range(5)])
    session.commit()
    pending = get_pending_articles(session, limit=3)
    assert [a.title for a in pending] == ["Story 0", "Story 1", "Story 2"]
    assert count_pending_articles(session) == 5


def test_record_classifications(session, feeds):
    insert_new_articles(session, [article(1), article(2), article(3)])
    session.commit()
    a1, a2, _ = get_pending_articles(session)

    record_classifications(
        session,
        [
            Classification(
                a1.id,
                ArticleStatus.KEPT,
                category="grid",
                reason="About ISOs",
                model="gpt-oss-120b",
                rules_version="v1",
            ),
            Classification(a2.id, ArticleStatus.REJECTED, reason="Celebrity EV"),
        ],
    )
    session.commit()
    session.expire_all()

    kept = session.get(Article, a1.id)
    assert kept.status is ArticleStatus.KEPT
    assert (kept.category, kept.reason, kept.model, kept.rules_version) == (
        "grid",
        "About ISOs",
        "gpt-oss-120b",
        "v1",
    )
    assert kept.classified_at is not None
    assert kept.classification_attempts == 1
    assert session.get(Article, a2.id).status is ArticleStatus.REJECTED
    assert [a.title for a in get_pending_articles(session)] == ["Story 3"]


def test_record_classifications_rejects_non_final_status(session, feeds):
    with pytest.raises(ValueError, match="kept or rejected"):
        record_classifications(session, [Classification(1, ArticleStatus.PENDING)])


def test_classification_failures_retry_then_give_up(session, feeds):
    insert_new_articles(session, [article(1), article(2)])
    session.commit()
    a1, a2 = get_pending_articles(session)

    for _ in range(2):
        record_classification_failure(session, [a1.id], max_attempts=3)
    session.commit()
    session.expire_all()
    assert session.get(Article, a1.id).status is ArticleStatus.PENDING
    assert session.get(Article, a1.id).classification_attempts == 2

    record_classification_failure(session, [a1.id], max_attempts=3)
    session.commit()
    session.expire_all()
    assert session.get(Article, a1.id).status is ArticleStatus.FAILED
    assert [a.id for a in get_pending_articles(session)] == [a2.id]

    # Already-classified articles aren't touched.
    record_classifications(session, [Classification(a2.id, ArticleStatus.KEPT)])
    record_classification_failure(session, [a2.id], max_attempts=1)
    session.commit()
    session.expire_all()
    assert session.get(Article, a2.id).status is ArticleStatus.KEPT


def test_pending_order_uses_fetched_at(session, feeds):
    insert_new_articles(session, [article(1), article(2)])
    session.commit()
    a1, a2 = get_pending_articles(session)
    session.get(Article, a2.id).fetched_at = datetime.now(UTC) - timedelta(days=1)
    session.commit()
    assert [a.id for a in get_pending_articles(session)] == [a2.id, a1.id]
