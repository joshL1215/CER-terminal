from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text, func, true
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


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
