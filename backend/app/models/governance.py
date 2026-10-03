import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Index, Integer, SmallInteger, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at, uuid_pk


class ShareLink(Base):
    __tablename__ = "share_link"

    id: Mapped[uuid.UUID] = uuid_pk()
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("report.id", ondelete="CASCADE"), index=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(Text, unique=True)
    label: Mapped[str | None] = mapped_column(Text)  # who it is for, e.g. "Dr. Nayak"; the owner's own reminder
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    views: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at()


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = uuid_pk()
    explanation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("explanation.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="SET NULL")
    )
    rating: Mapped[int] = mapped_column(SmallInteger)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at()


class SafetyReview(Base):
    """A clinical reviewer's verdict on something the safety checks did: a blocked explanation, a question's reply,
    or an explanation a reader found unhelpful. The latest verdict for a subject is its current one."""

    __tablename__ = "safety_review"
    __table_args__ = (Index("ix_safety_review_subject", "subject_type", "subject_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    subject_type: Mapped[str] = mapped_column(Text)  # explanation | question | feedback
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="SET NULL")
    )
    verdict: Mapped[str] = mapped_column(Text)  # correct | incorrect
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at()


class AuditLog(Base):
    """Append-only access and change log. Never stores health values."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(Text)
    entity_type: Mapped[str] = mapped_column(Text)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    meta: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB)
