from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class ArticleStatus(StrEnum):
    PENDING = "pending"  # stored, not yet classified
    KEPT = "kept"  # LLM judged relevant
    REJECTED = "rejected"  # filtered out by keyword rules or the LLM
    FAILED = "failed"  # classification failed too many times; skipped from now on


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
