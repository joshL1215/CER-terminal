from datetime import UTC, datetime

import pytest

from app.fetch import FeedParseError, parse_entries
from app.fetch.parse import to_plain_text, truncate

RSS = b"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>Alpha</title>
  <item>
    <title>Grid &amp; storage update</title>
    <link>https://alpha.example.com/a</link>
    <description>&lt;p&gt;New &lt;b&gt;battery&lt;/b&gt; record.&lt;/p&gt;</description>
    <pubDate>Mon, 02 Nov 2026 14:30:00 GMT</pubDate>
  </item>
  <item><title>No link</title></item>
  <item><link>https://alpha.example.com/no-title</link></item>
  <item><title>Bad link</title><link>mailto:someone@example.com</link></item>
  <item><title>Undated</title><link>https://alpha.example.com/b</link></item>
</channel></rss>"""

ATOM = b"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>Beta</title>
  <entry>
    <title>Atom story</title>
    <link href="https://beta.example.com/x"/>
    <updated>2026-11-01T08:00:00Z</updated>
    <summary>Plain summary</summary>
  </entry>
</feed>"""


def test_parse_rss():
    articles = parse_entries("alpha", RSS)
    assert [a.title for a in articles] == ["Grid & storage update", "Undated"]
    first = articles[0]
    assert first.feed_id == "alpha"
    assert first.url == "https://alpha.example.com/a"
    assert first.description == "New battery record."
    assert first.published_at == datetime(2026, 11, 2, 14, 30, tzinfo=UTC)
    assert articles[1].published_at is None
    assert articles[1].description is None


def test_parse_atom_uses_updated_date():
    (article,) = parse_entries("beta", ATOM)
    assert article.url == "https://beta.example.com/x"
    assert article.description == "Plain summary"
    assert article.published_at == datetime(2026, 11, 1, 8, 0, tzinfo=UTC)


def test_parse_rejects_non_feed():
    with pytest.raises(FeedParseError):
        parse_entries("alpha", b"<html><body>Access denied</body></html")


def test_empty_valid_feed_has_no_articles():
    assert (
        parse_entries("alpha", b'<rss version="2.0"><channel><title>x</title></channel></rss>')
        == []
    )


def test_plain_text_and_truncate():
    assert to_plain_text("<p>a&nbsp;b</p>\n\n<br/>c") == "a b c"
    assert to_plain_text(None) == ""
    long = "word " * 200
    cut = truncate(long.strip(), 50)
    assert len(cut) <= 50
    assert cut.endswith("…")
    assert truncate("short", 50) == "short"
