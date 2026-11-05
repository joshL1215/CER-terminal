"""One ingest run: sync feeds → fetch → store new articles → classify."""

import asyncio
import logging
from dataclasses import dataclass, field

import httpx
from cer_db import FeedRecord, session_scope
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.classify import ChatClient, ClassifyStats, Provider, classify_pending
from app.feeds import FeedRegistry
from app.fetch import FeedRequest, FetchResult, FetchStatus, fetch_all
from app.repository import (
    insert_new_articles,
    record_fetch_failure,
    record_fetch_success,
    sync_feeds,
)
from app.rules import RelevanceRules

logger = logging.getLogger(__name__)


@dataclass
class IngestSummary:
    feeds_ok: int = 0
    feeds_not_modified: int = 0
    feeds_failed: int = 0
    new_articles: int = 0
    classify: ClassifyStats | None = None
    failed_feeds: dict[str, str] = field(default_factory=dict)


def _feed_requests(factory: sessionmaker[Session], registry: FeedRegistry) -> list[FeedRequest]:
    with session_scope(factory) as session:
        sync_feeds(session, registry)
        records = session.scalars(select(FeedRecord).where(FeedRecord.active.is_(True))).all()
        return [
            FeedRequest(record.id, record.url, record.etag, record.last_modified)
            for record in records
        ]


def _store(factory: sessionmaker[Session], result: FetchResult, summary: IngestSummary) -> None:
    feed_id = result.request.feed_id
    with session_scope(factory) as session:
        if result.status is FetchStatus.FAILED:
            record_fetch_failure(session, feed_id, result.error or "unknown error")
            summary.feeds_failed += 1
            summary.failed_feeds[feed_id] = result.error or "unknown error"
            logger.warning("%s: fetch failed: %s", feed_id, result.error)
            return

        new = insert_new_articles(session, result.articles) if result.articles else 0
        record_fetch_success(session, feed_id, etag=result.etag, last_modified=result.last_modified)
    summary.new_articles += new
    if result.status is FetchStatus.NOT_MODIFIED:
        summary.feeds_not_modified += 1
        logger.info("%s: not modified", feed_id)
    else:
        summary.feeds_ok += 1
        logger.info("%s: %d items, %d new", feed_id, len(result.articles), new)


def run_ingest(
    factory: sessionmaker[Session],
    registry: FeedRegistry,
    rules: RelevanceRules,
    *,
    providers: list[Provider],
    chat_client: ChatClient,
    classify: bool = True,
    batch_size: int = 20,
    max_batches: int = 25,
    transport: httpx.AsyncBaseTransport | None = None,
) -> IngestSummary:
    summary = IngestSummary()

    requests = _feed_requests(factory, registry)
    logger.info("fetching %d active feeds", len(requests))
    for result in asyncio.run(fetch_all(requests, transport=transport)):
        _store(factory, result, summary)

    if not classify:
        logger.info("classification skipped (--skip-classify)")
    elif not providers:
        logger.warning("classification skipped: no LLM configured (set LLM_BASE_URL, ...)")
    else:
        summary.classify = classify_pending(
            factory,
            rules,
            providers,
            chat_client,
            batch_size=batch_size,
            max_batches=max_batches,
        )
    return summary
