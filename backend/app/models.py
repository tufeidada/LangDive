from datetime import datetime, date
from sqlalchemy import (
    String, Integer, Float, Boolean, Text, Date, DateTime, JSON,
    ForeignKey, CheckConstraint, UniqueConstraint, Index
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class Content(Base):
    __tablename__ = "content"
    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    difficulty: Mapped[str | None] = mapped_column(String)
    tags: Mapped[dict | None] = mapped_column(JSON)
    content_text: Mapped[str | None] = mapped_column(Text)
    summary_zh: Mapped[str | None] = mapped_column(Text)
    audio_path: Mapped[str | None] = mapped_column(Text)
    words_json: Mapped[dict | None] = mapped_column(JSON)
    preview_words_json: Mapped[dict | None] = mapped_column(JSON)
    segment_count: Mapped[int] = mapped_column(Integer, default=1)
    has_subtitles: Mapped[bool] = mapped_column(Boolean, default=True)
    date: Mapped[date] = mapped_column(Date)
    duration: Mapped[str | None] = mapped_column(Text)
    read_time: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    segments: Mapped[list["ContentSegment"]] = relationship(back_populates="content", cascade="all, delete-orphan")
    __table_args__ = (
        CheckConstraint("type IN ('article', 'video')"),
        CheckConstraint("difficulty IN ('A2', 'B1', 'B2', 'C1')"),
    )


class ContentSegment(Base):
    __tablename__ = "content_segment"
    id: Mapped[int] = mapped_column(primary_key=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("content.id", ondelete="CASCADE"))
    segment_index: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(Text)
    start_time: Mapped[float | None] = mapped_column(Float)
    end_time: Mapped[float | None] = mapped_column(Float)
    text_en: Mapped[str] = mapped_column(Text)
    summary_zh: Mapped[str | None] = mapped_column(Text)
    audio_en_path: Mapped[str | None] = mapped_column(Text)
    preview_words_json: Mapped[dict | None] = mapped_column(JSON)
    words_json: Mapped[dict | None] = mapped_column(JSON)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    content: Mapped["Content"] = relationship(back_populates="segments")
    __table_args__ = (UniqueConstraint("content_id", "segment_index"),)


class Vocabulary(Base):
    __tablename__ = "vocabulary"
    id: Mapped[int] = mapped_column(primary_key=True)
    word: Mapped[str] = mapped_column(Text, unique=True)
    ipa: Mapped[str | None] = mapped_column(Text)
    meaning_zh: Mapped[str] = mapped_column(Text)
    detail_zh: Mapped[str | None] = mapped_column(Text)
    example_en: Mapped[str | None] = mapped_column(Text)
    example_zh: Mapped[str | None] = mapped_column(Text)
    level: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="unknown")
    encounter_count: Mapped[int] = mapped_column(Integer, default=0)
    lookup_count: Mapped[int] = mapped_column(Integer, default=0)
    srs_level: Mapped[int] = mapped_column(Integer, default=0)
    next_review: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_reviewed: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_reviews: Mapped[int] = mapped_column(Integer, default=0)
    easy_streak: Mapped[int] = mapped_column(Integer, default=0)
    again_count: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str | None] = mapped_column(Text)
    added_method: Mapped[str] = mapped_column(String, default="auto")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    __table_args__ = (
        CheckConstraint("level IN ('CET-4', 'CET-6', 'IELTS', 'Advanced')"),
        CheckConstraint("status IN ('unknown', 'fuzzy', 'known', 'focus', 'ignored')"),
        CheckConstraint("added_method IN ('auto', 'manual', 'preview')"),
    )


class EventLog(Base):
    __tablename__ = "event_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(Text)
    content_id: Mapped[int | None] = mapped_column(Integer)
    segment_index: Mapped[int | None] = mapped_column(Integer)
    word: Mapped[str | None] = mapped_column(Text)
    extra_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        Index("idx_event_type", "event_type"),
        Index("idx_event_created", "created_at"),
    )


class CachedAsset(Base):
    __tablename__ = "cached_asset"
    id: Mapped[int] = mapped_column(primary_key=True)
    content_hash: Mapped[str] = mapped_column(Text)
    asset_type: Mapped[str] = mapped_column(Text)
    provider: Mapped[str | None] = mapped_column(Text)
    version: Mapped[str] = mapped_column(Text, default="1")
    file_path: Mapped[str | None] = mapped_column(Text)
    text_content: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("content_hash", "asset_type", "provider", "version"),)


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SearchQueryLog(Base):
    __tablename__ = "search_query_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    query: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text)
    result_count: Mapped[int | None] = mapped_column(Integer)
    date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
