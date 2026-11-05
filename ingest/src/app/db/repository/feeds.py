"""Feed queries: syncing feeds.yaml into the DB and tracking fetch results."""

from datetime import UTC, datetime

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.feeds import FeedRegistry

from ..models import FeedRecord
from ._upsert import upsert_insert

MAX_ERROR_LENGTH = 2000
METADATA_COLUMNS = ("name", "url", "source_type", "category", "tags", "active", "llm_context")


def sync_feeds(session: Session, registry: FeedRegistry) -> None:
    """Mirror feeds.yaml into the feeds table.

    Inserts new feeds, updates metadata on existing ones, and marks feeds that
    were removed from the YAML as inactive (kept, since articles reference them).
    Fetch state (etag, failures, ...) is left untouched.
    """
    now = datetime.now(UTC)
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
    stmt = upsert_insert(session, FeedRecord).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[FeedRecord.id],
        set_={column: stmt.excluded[column] for column in METADATA_COLUMNS} | {"updated_at": now},
    )
    session.execute(stmt)

    yaml_ids = [feed.id for feed in registry.feeds]
    session.execute(
        update(FeedRecord)
        .where(FeedRecord.id.not_in(yaml_ids), FeedRecord.active.is_(True))
        .values(active=False, updated_at=now)
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
    at = at or datetime.now(UTC)
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
            last_fetched_at=at or datetime.now(UTC),
            consecutive_failures=FeedRecord.consecutive_failures + 1,
            last_error=error[:MAX_ERROR_LENGTH],
        )
    )
