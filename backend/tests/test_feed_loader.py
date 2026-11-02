import textwrap

import pytest

from app.feeds import (
    DEFAULT_FEEDS_PATH,
    FeedConfigError,
    SourceType,
    load_feed_registry,
    parse_feed_registry,
)


def parse(text: str):
    return parse_feed_registry(textwrap.dedent(text))


def test_bundled_feeds_yaml_is_valid():
    registry = load_feed_registry(DEFAULT_FEEDS_PATH)
    assert registry.feeds
    assert all(feed.active for feed in registry.active())


def test_defaults_apply_and_feeds_override():
    registry = parse(
        """
        version: 1
        defaults:
          category: general
          source_type: trade
          tags: [energy]
        feeds:
          - id: one
            name: One
            url: https://example.com/one.xml
          - id: two
            name: Two
            url: https://example.com/two.xml
            category: Grid
            source_type: government
            tags: [Grid, grid, ' policy ']
            active: false
        """
    )
    one, two = registry.feeds
    assert one.category == "general"
    assert one.source_type is SourceType.TRADE
    assert one.tags == ("energy",)
    assert one.active is True
    assert two.category == "grid"
    assert two.source_type is SourceType.GOVERNMENT
    assert two.tags == ("grid", "policy")
    assert [feed.id for feed in registry.active()] == ["one"]
    assert registry.get("two") is two
    assert registry.get("missing") is None


def test_llm_context_whitespace_is_collapsed():
    registry = parse(
        """
        version: 1
        feeds:
          - id: one
            name: One
            url: https://example.com/feed
            llm_context: >
              Line one
              line two.
        """
    )
    assert registry.feeds[0].llm_context == "Line one line two."


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("version: 2\nfeeds: [{id: a, name: A, url: 'https://x.com/a'}]", "unsupported"),
        ("version: 1\nfeeds: []", "non-empty list"),
        ("version: 1\nfeeds: [{id: Bad_ID, name: A, url: 'https://x.com/a'}]", "lowercase slug"),
        ("version: 1\nfeeds: [{id: a, name: A, url: 'ftp://x.com/a'}]", "http(s) URL"),
        ("version: 1\nfeeds: [{id: a, name: A, url: 'https://x.com/a', colour: red}]", "colour"),
        (
            "version: 1\nfeeds: [{id: a, name: A, url: 'https://x.com/a', source_type: blog}]",
            "source_type",
        ),
        ("version: 1\nfeeds: [{id: a, name: A}]", "url"),
        ("version: 1\nfeedz: []", "unknown top-level"),
        ("- just\n- a list", "top level must be a mapping"),
        ("version: 1\nfeeds: [{id: a, name: A, url: 'https://x.com/a'", "invalid YAML"),
    ],
)
def test_invalid_configs_raise_readable_errors(body, message):
    with pytest.raises(FeedConfigError, match=message.replace("(", r"\(").replace(")", r"\)")):
        parse_feed_registry(body)


def test_duplicate_ids_and_urls_rejected():
    with pytest.raises(FeedConfigError, match="duplicate feed id 'a'"):
        parse(
            """
            version: 1
            feeds:
              - {id: a, name: A, url: 'https://x.com/a'}
              - {id: a, name: B, url: 'https://x.com/b'}
            """
        )
    with pytest.raises(FeedConfigError, match="same url"):
        parse(
            """
            version: 1
            feeds:
              - {id: a, name: A, url: 'https://x.com/feed'}
              - {id: b, name: B, url: 'https://X.com/feed/'}
            """
        )


def test_duplicate_yaml_keys_rejected():
    with pytest.raises(FeedConfigError, match="duplicate key 'url' on line 7"):
        parse(
            """
            version: 1
            feeds:
              - id: a
                name: A
                url: https://x.com/a
                url: https://x.com/b
            """
        )


def test_error_message_names_the_feed():
    with pytest.raises(FeedConfigError, match=r"feeds\[1\] \(broken\)\.url"):
        parse(
            """
            version: 1
            feeds:
              - {id: ok, name: OK, url: 'https://x.com/a'}
              - {id: broken, name: Broken, url: 'not a url'}
            """
        )


def test_missing_file():
    with pytest.raises(FeedConfigError, match="could not read"):
        load_feed_registry("/nonexistent/feeds.yaml")
