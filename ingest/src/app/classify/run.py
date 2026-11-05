"""Classify pending articles batch by batch and record the decisions."""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass

from cer_db import ArticleStatus, FeedRecord, session_scope
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.repository import (
    Classification,
    get_pending_articles,
    record_classification_failure,
    record_classifications,
)
from app.rules import RelevanceRules

from .llm import AllProvidersFailed, ChatClient, decide
from .prompt import ArticleInput, build_messages
from .providers import Provider

logger = logging.getLogger(__name__)

KEYWORD_FILTER_MODEL = "keyword-filter"


@dataclass
class ClassifyStats:
    batches: int = 0
    kept: int = 0
    rejected: int = 0
    unanswered: int = 0  # LLM skipped or failed; stays pending for a later run
    failed: int = 0  # gave up after too many attempts


def _load_batch(
    factory: sessionmaker[Session], batch_size: int, seen: set[int]
) -> list[ArticleInput]:
    with session_scope(factory) as session:
        articles = get_pending_articles(session, limit=batch_size, exclude_ids=seen)
        feeds = {feed.id: feed for feed in session.scalars(select(FeedRecord))}
        return [
            ArticleInput(
                id=article.id,
                title=article.title,
                description=article.description,
                source=feeds[article.feed_id].name,
                source_category=feeds[article.feed_id].category,
                source_context=feeds[article.feed_id].llm_context,
            )
            for article in articles
        ]


def _keyword_rejections(rules: RelevanceRules, batch: list[ArticleInput]) -> list[Classification]:
    rejections = []
    for article in batch:
        keyword = rules.keyword_match(article.title)
        if keyword:
            rejections.append(
                Classification(
                    article.id,
                    ArticleStatus.REJECTED,
                    reason=f'keyword pre-filter: "{keyword}"',
                    model=KEYWORD_FILTER_MODEL,
                    rules_version=rules.version,
                )
            )
    return rejections


def classify_pending(
    factory: sessionmaker[Session],
    rules: RelevanceRules,
    providers: list[Provider],
    client: ChatClient,
    *,
    batch_size: int = 40,
    max_batches: int = 25,
    max_attempts: int = 3,
    sleep: Callable[[float], None] = time.sleep,
) -> ClassifyStats:
    """Each pending article is tried at most once per run."""
    stats = ClassifyStats()
    seen: set[int] = set()

    while stats.batches < max_batches:
        batch = _load_batch(factory, batch_size, seen)
        if not batch:
            break
        stats.batches += 1
        seen.update(article.id for article in batch)

        results = _keyword_rejections(rules, batch)
        filtered = {result.article_id for result in results}
        to_ask = [article for article in batch if article.id not in filtered]
        unanswered: list[int] = []

        if to_ask:
            ids = [article.id for article in to_ask]
            try:
                outcome = decide(
                    build_messages(rules, to_ask),
                    ids,
                    rules.categories,
                    providers,
                    client,
                    sleep=sleep,
                )
            except AllProvidersFailed as exc:
                logger.error("batch %d: %s", stats.batches, exc)
                unanswered = ids
            else:
                for article_id in ids:
                    decision = outcome.decisions.get(article_id)
                    if decision is None:
                        unanswered.append(article_id)
                        continue
                    results.append(
                        Classification(
                            article_id,
                            ArticleStatus.KEPT if decision.keep else ArticleStatus.REJECTED,
                            category=decision.category,
                            reason=decision.reason or None,
                            model=outcome.provider.label,
                            rules_version=rules.version,
                        )
                    )

        with session_scope(factory) as session:
            record_classifications(session, results)
            stats.failed += record_classification_failure(
                session, unanswered, max_attempts=max_attempts
            )
        kept = sum(result.status is ArticleStatus.KEPT for result in results)
        stats.kept += kept
        stats.rejected += len(results) - kept
        stats.unanswered += len(unanswered)
        logger.info(
            "batch %d: %d kept, %d rejected, %d unanswered",
            stats.batches,
            kept,
            len(results) - kept,
            len(unanswered),
        )

    return stats
