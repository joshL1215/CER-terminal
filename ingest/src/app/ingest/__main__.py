"""Run the daily ingest: `uv run python -m app.ingest [--skip-classify] [--max-batches N]`."""

import argparse
import logging
import sys

from cer_db import DatabaseConfigError, make_engine, make_session_factory
from sqlalchemy.exc import SQLAlchemyError

from app.classify import OpenAICompatibleClient, ProviderConfigError, providers_from_env
from app.feeds import DEFAULT_FEEDS_PATH, FeedConfigError, load_feed_registry
from app.rules import DEFAULT_RULES_PATH, RulesConfigError, load_rules

from .pipeline import IngestSummary, run_ingest

logger = logging.getLogger("app.ingest")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m app.ingest")
    parser.add_argument("--feeds", default=DEFAULT_FEEDS_PATH, help="path to feeds.yaml")
    parser.add_argument("--rules", default=DEFAULT_RULES_PATH, help="path to rules.yaml")
    parser.add_argument("--skip-classify", action="store_true", help="fetch only, no LLM calls")
    parser.add_argument("--batch-size", type=int, default=40, help="articles per LLM call")
    parser.add_argument("--max-batches", type=int, default=25, help="LLM calls per run")
    return parser.parse_args(argv)


def _log_summary(summary: IngestSummary) -> None:
    logger.info(
        "feeds: %d ok, %d not modified, %d failed; %d new articles",
        summary.feeds_ok,
        summary.feeds_not_modified,
        summary.feeds_failed,
        summary.new_articles,
    )
    if summary.classify:
        stats = summary.classify
        logger.info(
            "classified in %d batches: %d kept, %d rejected, %d left pending, %d failed",
            stats.batches,
            stats.kept,
            stats.rejected,
            stats.unanswered,
            stats.failed,
        )


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    args = _parse_args(sys.argv[1:] if argv is None else argv)

    try:
        registry = load_feed_registry(args.feeds)
        rules = load_rules(args.rules)
        providers = [] if args.skip_classify else providers_from_env()
        engine = make_engine()
    except (FeedConfigError, RulesConfigError, ProviderConfigError, DatabaseConfigError) as exc:
        logger.error("config error: %s", exc)
        return 2

    try:
        summary = run_ingest(
            make_session_factory(engine),
            registry,
            rules,
            providers=providers,
            chat_client=OpenAICompatibleClient(),
            classify=not args.skip_classify,
            batch_size=args.batch_size,
            max_batches=args.max_batches,
        )
    except SQLAlchemyError as exc:
        logger.error("database error: %s", exc)
        return 1
    finally:
        engine.dispose()

    _log_summary(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
