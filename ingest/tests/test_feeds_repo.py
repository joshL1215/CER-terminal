from app.db import (
    get_feed,
    record_fetch_failure,
    record_fetch_success,
    sync_feeds,
)
from app.feeds import parse_feed_registry


def test_sync_feeds_inserts_metadata(session, feeds):
    alpha = get_feed(session, "alpha")
    assert alpha.name == "Alpha News"
    assert alpha.category == "grid"
    assert alpha.tags == ["utilities"]
    assert alpha.source_type == "news"
    assert alpha.llm_context == "Alpha context."
    assert alpha.active is True
    assert alpha.consecutive_failures == 0
    assert get_feed(session, "beta").active is False


def test_sync_feeds_updates_and_deactivates_without_touching_fetch_state(session, feeds):
    record_fetch_success(session, "alpha", etag='"v1"', last_modified="Mon, 01 Jan 2026")
    session.commit()

    updated = parse_feed_registry(
        """
        version: 1
        feeds:
          - id: alpha
            name: Alpha Renamed
            url: https://alpha.example.com/rss
            tags: [grid, policy]
        """
    )
    sync_feeds(session, updated)
    session.commit()
    session.expire_all()

    alpha = get_feed(session, "alpha")
    assert alpha.name == "Alpha Renamed"
    assert alpha.tags == ["grid", "policy"]
    assert alpha.etag == '"v1"'
    assert alpha.last_modified == "Mon, 01 Jan 2026"
    # Removed from the YAML: kept for article history, but inactive.
    assert get_feed(session, "beta").active is False


def test_sync_feeds_deactivates_removed_feed(session):
    sync_feeds(
        session,
        parse_feed_registry(
            "version: 1\nfeeds:\n"
            "  - {id: a, name: A, url: 'https://a.example.com/rss'}\n"
            "  - {id: b, name: B, url: 'https://b.example.com/rss'}\n"
        ),
    )
    session.commit()
    sync_feeds(
        session,
        parse_feed_registry(
            "version: 1\nfeeds: [{id: a, name: A, url: 'https://a.example.com/rss'}]"
        ),
    )
    session.commit()
    session.expire_all()
    assert get_feed(session, "a").active is True
    assert get_feed(session, "b").active is False


def test_fetch_failure_then_success(session, feeds):
    record_fetch_failure(session, "alpha", "timeout")
    record_fetch_failure(session, "alpha", "x" * 5000)
    session.commit()
    session.expire_all()
    alpha = get_feed(session, "alpha")
    assert alpha.consecutive_failures == 2
    assert len(alpha.last_error) == 2000
    assert alpha.last_success_at is None
    assert alpha.last_fetched_at is not None

    record_fetch_success(session, "alpha", etag='"v2"')
    session.commit()
    session.expire_all()
    alpha = get_feed(session, "alpha")
    assert alpha.consecutive_failures == 0
    assert alpha.last_error is None
    assert alpha.etag == '"v2"'
    assert alpha.last_success_at is not None
