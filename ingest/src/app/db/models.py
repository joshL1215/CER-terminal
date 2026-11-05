"""Database schema owned by the ingest service.

Other services (e.g. the web API) read these tables but don't migrate them;
schema changes go through this service's Alembic migrations.
"""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Text,
    func,
    true,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Stable constraint names so Alembic migrations are predictable across databases.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class ArticleStatus(StrEnum):
    PENDING = "pending"  # stored, not yet classified
    KEPT = "kept"  # LLM judged relevant
    REJECTED = "rejected"  # filtered out by keyword rules or the LLM
    FAILED = "failed"  # classification failed too many times; skipped from now on


class FeedRecord(Base):
    """A feed from config/feeds.yaml, mirrored into the DB, plus its fetch state.

    The YAML file is the source of truth for metadata; it's synced in on every
    run so other services can show source names without reading the YAML.
    """

    __tablename__ = "feeds"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(32))
    category: Mapped[str] = mapped_column(String(64))
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    active: Mapped[bool] = mapped_column(default=True, server_default=true())
    llm_context: Mapped[str | None] = mapped_column(Text)

    # Conditional GET state, so unchanged feeds can answer 304 Not Modified.
    etag: Mapped[str | None] = mapped_column(Text)
    last_modified: Mapped[str | None] = mapped_column(Text)

    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_error: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Article(Base):
    """One item from a feed, plus the relevance decision made about it."""

    __tablename__ = "articles"
    __table_args__ = (
        Index("ix_articles_status", "status"),
        Index("ix_articles_feed_id", "feed_id"),
        Index("ix_articles_published_at", "published_at"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    # sha256 of the canonical URL; the dedupe key across runs and feeds.
    url_hash: Mapped[str] = mapped_column(String(64), unique=True)
    url: Mapped[str] = mapped_column(Text)
    feed_id: Mapped[str] = mapped_column(ForeignKey("feeds.id"))

    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    status: Mapped[ArticleStatus] = mapped_column(
        Enum(
            ArticleStatus,
            name="article_status",
            native_enum=False,
            length=16,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        default=ArticleStatus.PENDING,
        server_default=ArticleStatus.PENDING.value,
    )
    category: Mapped[str | None] = mapped_column(String(64))
    reason: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(String(100))  # which LLM made the call
    rules_version: Mapped[str | None] = mapped_column(String(64))
    classified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    classification_attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
