"""Typed models for the RSS feed registry (config/feeds.yaml)."""

import re
from enum import StrEnum
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

FEED_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")  # validates id format
SUPPORTED_VERSIONS = {1}


class SourceType(StrEnum):
    NEWS = "news"
    TRADE = "trade"
    GOVERNMENT = "government"
    RESEARCH = "research"
    UTILITY = "utility"
    OTHER = "other"


class FeedDefaults(BaseModel):
    """Values applied to every feed unless the feed sets its own."""

    model_config = ConfigDict(extra="forbid")

    active: bool = True
    source_type: SourceType = SourceType.NEWS
    category: str = "general"
    tags: list[str] = Field(default_factory=list)


class Feed(BaseModel):
    """A single RSS/Atom feed and the metadata the ingest job and LLM use."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    name: str = Field(min_length=1)
    url: str
    source_type: SourceType = SourceType.NEWS
    category: str = "general"
    tags: tuple[str, ...] = ()
    active: bool = True
    llm_context: str | None = None

    @field_validator("id")
    @classmethod
    def _check_id(cls, value: str) -> str:
        if not FEED_ID_PATTERN.fullmatch(value):
            raise ValueError(
                "must be a lowercase slug (letters, digits, single hyphens), "
                f"e.g. 'utility-dive'; got {value!r}"
            )
        return value

    @field_validator("url")
    @classmethod
    def _check_url(cls, value: str) -> str:
        value = value.strip()
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError(f"must be an absolute http(s) URL; got {value!r}")
        return value

    @field_validator("category")
    @classmethod
    def _normalize_category(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("tags", mode="before")
    @classmethod
    def _normalize_tags(cls, value: object) -> object:
        if isinstance(value, (list, tuple)):
            # Lowercase, strip, and drop duplicates while keeping order.
            return tuple(dict.fromkeys(str(tag).strip().lower() for tag in value if tag))
        return value

    @field_validator("llm_context")
    @classmethod
    def _strip_context(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return " ".join(value.split()) or None


class FeedRegistry(BaseModel):
    """The whole feeds.yaml document after defaults have been applied."""

    model_config = ConfigDict(extra="forbid")

    version: int
    feeds: tuple[Feed, ...]

    @field_validator("version")
    @classmethod
    def _check_version(cls, value: int) -> int:
        if value not in SUPPORTED_VERSIONS:
            raise ValueError(
                f"unsupported feeds.yaml version {value}; expected one of {SUPPORTED_VERSIONS}"
            )
        return value

    # prohibits duplicate urls and ids
    @model_validator(mode="after")
    def _check_unique(self) -> "FeedRegistry":
        seen_ids: set[str] = set()
        seen_urls: dict[str, str] = {}
        for feed in self.feeds:
            if feed.id in seen_ids:
                raise ValueError(f"duplicate feed id {feed.id!r}")
            seen_ids.add(feed.id)

            url_key = feed.url.rstrip("/").lower()
            if url_key in seen_urls:
                raise ValueError(
                    f"feeds {seen_urls[url_key]!r} and {feed.id!r} have the same url {feed.url!r}"
                )
            seen_urls[url_key] = feed.id
        return self

    def active(self) -> list[Feed]:
        return [feed for feed in self.feeds if feed.active]

    def get(self, feed_id: str) -> Feed | None:
        return next((feed for feed in self.feeds if feed.id == feed_id), None)
