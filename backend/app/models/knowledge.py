import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    REAL,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at, pg_enum, uuid_pk
from app.models.enums import Lang, SafetyStatus

EMBEDDING_DIM = 384  # intfloat/multilingual-e5-small


class KbDocument(Base):
    __tablename__ = "kb_document"

    id: Mapped[uuid.UUID] = uuid_pk()
    title: Mapped[str] = mapped_column(Text)
    source_org: Mapped[str] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    license: Mapped[str] = mapped_column(Text)
    language: Mapped[Lang] = mapped_column(pg_enum(Lang, "lang"), default=Lang.EN)
    retrieved_at: Mapped[date | None] = mapped_column(Date)
    checksum: Mapped[str] = mapped_column(Text)


class KbChunk(Base):
    __tablename__ = "kb_chunk"
    __table_args__ = (
        Index(
            "ix_kb_chunk_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("kb_document.id", ondelete="CASCADE"), index=True
    )
    test_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("lab_test.id"), index=True)
    chunk_index: Mapped[int] = mapped_column(SmallInteger)
    content: Mapped[str] = mapped_column(Text)
    language: Mapped[Lang] = mapped_column(pg_enum(Lang, "lang"), default=Lang.EN)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM))
    token_count: Mapped[int] = mapped_column(Integer)


class Explanation(Base):
    __tablename__ = "explanation"

    id: Mapped[uuid.UUID] = uuid_pk()
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("report.id", ondelete="CASCADE"), index=True
    )
    language: Mapped[Lang] = mapped_column(pg_enum(Lang, "lang"))
    model_id: Mapped[str] = mapped_column(Text)
    prompt_version: Mapped[str] = mapped_column(Text)
    content: Mapped[dict[str, Any]] = mapped_column(JSONB)
    safety_status: Mapped[SafetyStatus] = mapped_column(pg_enum(SafetyStatus, "safety_status"))
    audio_key: Mapped[str | None] = mapped_column(Text)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = created_at()


class ExplanationCitation(Base):
    __tablename__ = "explanation_citation"

    explanation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("explanation.id", ondelete="CASCADE"), primary_key=True
    )
    kb_chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("kb_chunk.id", ondelete="CASCADE"), primary_key=True
    )
    rank: Mapped[int] = mapped_column(SmallInteger)


class TrendInsight(Base):
    """The latest analysis per profile × test, kept for the profile page. Recomputed whenever a report is
    confirmed or deleted; the per-report detail lives in observation.analysis."""

    __tablename__ = "trend_insight"
    __table_args__ = (UniqueConstraint("profile_id", "test_id", name="uq_trend_insight_profile_test"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profile.id", ondelete="CASCADE"))
    test_id: Mapped[int] = mapped_column(Integer, ForeignKey("lab_test.id"))
    last_observation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("observation.id", ondelete="CASCADE")
    )
    n_points: Mapped[int] = mapped_column(SmallInteger)
    slope_per_year: Mapped[Decimal | None] = mapped_column(Numeric)
    direction: Mapped[str | None] = mapped_column(Text)  # rising | falling | flat; None below three results
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    rcv_significant: Mapped[bool | None] = mapped_column(Boolean)
    projected_crossing: Mapped[date | None] = mapped_column(Date)
    percentile: Mapped[float | None] = mapped_column(REAL)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
