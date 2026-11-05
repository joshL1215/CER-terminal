"""Turn raw RSS/Atom bytes into NewArticle items."""

import html
import re
from datetime import UTC, datetime

import feedparser

from app.repository import NewArticle

MAX_DESCRIPTION_LENGTH = 500
_TAG = re.compile(r"<[^>]+>")


class FeedParseError(ValueError):
    pass


def to_plain_text(value: str | None) -> str:
    """Strip HTML tags and entities and collapse whitespace."""
    if not value:
        return ""
    return " ".join(html.unescape(_TAG.sub(" ", value)).split())


def truncate(text: str, limit: int = MAX_DESCRIPTION_LENGTH) -> str:
    if len(text) <= limit:
        return text
    cut = text[: limit - 1].rsplit(" ", 1)[0] or text[: limit - 1]
    return cut.rstrip(" ,.;:") + "…"


def _published_at(entry) -> datetime | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    return datetime(*parsed[:6], tzinfo=UTC)


def parse_entries(feed_id: str, content: bytes) -> list[NewArticle]:
    parsed = feedparser.parse(content)
    if parsed.bozo and not parsed.entries:
        raise FeedParseError(f"not a valid RSS/Atom feed: {parsed.get('bozo_exception')}")

    articles = []
    for entry in parsed.entries:
        link = (entry.get("link") or "").strip()
        title = to_plain_text(entry.get("title"))
        if not title or not link.startswith(("http://", "https://")):
            continue
        description = truncate(to_plain_text(entry.get("summary"))) or None
        articles.append(
            NewArticle(
                feed_id=feed_id,
                url=link,
                title=title,
                description=description,
                published_at=_published_at(entry),
            )
        )
    return articles
