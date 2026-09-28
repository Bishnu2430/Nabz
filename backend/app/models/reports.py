import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    REAL,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at, pg_enum, uuid_pk
from app.models.enums import JobStage, JobStatus, ObsStatus, ReportStatus


class Report(Base):
    __tablename__ = "report"
    __table_args__ = (
        Index("ix_report_profile_collected", "profile_id", text("collected_at DESC")),
        Index(
            "uq_report_profile_source",
            "profile_id",
            "source_sha256",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profile.id", ondelete="CASCADE"))
    uploaded_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("app_user.id"))
    lab_name: Mapped[str | None] = mapped_column(Text)
    collected_at: Mapped[date | None] = mapped_column(Date)
    status: Mapped[ReportStatus] = mapped_column(
        pg_enum(ReportStatus, "report_status"), default=ReportStatus.UPLOADED
    )
    source_sha256: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at()
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReportFile(Base):
    __tablename__ = "report_file"

    id: Mapped[uuid.UUID] = uuid_pk()
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("report.id", ondelete="CASCADE"), index=True
    )
    storage_key: Mapped[str] = mapped_column(Text)
    mime_type: Mapped[str] = mapped_column(Text)
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(Text)
    quality_score: Mapped[float | None] = mapped_column(REAL)
    created_at: Mapped[datetime] = created_at()


class ReportPage(Base):
    __tablename__ = "report_page"

    id: Mapped[uuid.UUID] = uuid_pk()
    report_file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("report_file.id", ondelete="CASCADE"), index=True
    )
    page_no: Mapped[int] = mapped_column(SmallInteger)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    ocr: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class ProcessingJob(Base):
    """Durable queue item; claimed with FOR UPDATE SKIP LOCKED (see ADR-0002)."""

    __tablename__ = "processing_job"
    __table_args__ = (
        Index("ix_processing_job_queued", "run_after", postgresql_where=text("status = 'queued'")),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("report.id", ondelete="CASCADE"), index=True
    )
    stage: Mapped[JobStage] = mapped_column(pg_enum(JobStage, "job_stage"))
    status: Mapped[JobStatus] = mapped_column(pg_enum(JobStatus, "job_status"), default=JobStatus.QUEUED)
    attempts: Mapped[int] = mapped_column(SmallInteger, default=0)
    run_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_by: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at()
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Observation(Base):
    """One result row. Raw text is kept next to the interpreted value for audit and re-processing."""

    __tablename__ = "observation"

    id: Mapped[uuid.UUID] = uuid_pk()
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("report.id", ondelete="CASCADE"), index=True
    )
    report_page_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("report_page.id", ondelete="SET NULL")
    )
    test_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("lab_test.id"), index=True)
    raw_name: Mapped[str | None] = mapped_column(Text)
    raw_value: Mapped[str | None] = mapped_column(Text)
    raw_unit: Mapped[str | None] = mapped_column(Text)
    raw_range: Mapped[str | None] = mapped_column(Text)
    raw_flag: Mapped[str | None] = mapped_column(Text)  # "H"/"L" as printed; cross-checked by the classifier
    section: Mapped[str | None] = mapped_column(Text)  # panel code of the report section (matching context)
    value_num: Mapped[Decimal | None] = mapped_column(Numeric)
    unit: Mapped[str | None] = mapped_column(Text)
    ref_low: Mapped[Decimal | None] = mapped_column(Numeric)
    ref_high: Mapped[Decimal | None] = mapped_column(Numeric)
    ref_source: Mapped[str] = mapped_column(Text, default="report")
    status: Mapped[ObsStatus] = mapped_column(pg_enum(ObsStatus, "obs_status"), default=ObsStatus.UNKNOWN)
    bbox: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    confidence: Mapped[float] = mapped_column(REAL, default=0.0)  # model's probability the row is right
    ocr_confidence: Mapped[float | None] = mapped_column(REAL)  # reader confidence (1.0 for PDF text layer)
    match_score: Mapped[float | None] = mapped_column(REAL)
    match_method: Mapped[str | None] = mapped_column(Text)  # exact | fuzzy | resolver | manual | none
    match_candidates: Mapped[list[Any] | None] = mapped_column(JSONB)  # [[test_code, score], ...] for review
    edited: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # As of this report's date: change since the previous result, trend, population percentile (app.services.analysis)
    analysis: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = created_at()
