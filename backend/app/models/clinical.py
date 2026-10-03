"""Doctors on Nabz (docs/12 §2): a clinician's registration, the reports a family shares with them, and their notes."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at, uuid_pk


class Clinician(Base):
    """A clinician account's medical-council registration. Reports can be shared with them only once an admin has
    checked it against the council's register (`verified_at`)."""

    __tablename__ = "clinician"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="CASCADE"), primary_key=True
    )
    full_name: Mapped[str] = mapped_column(Text)
    registration_no: Mapped[str] = mapped_column(Text)
    council: Mapped[str] = mapped_column(Text)  # e.g. "Odisha Council of Medical Registration"
    specialty: Mapped[str | None] = mapped_column(Text)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = created_at()


class ReportGrant(Base):
    """One report shared with one clinician account, until the family withdraws it."""

    __tablename__ = "report_grant"
    __table_args__ = (Index("ix_report_grant_clinician", "clinician_user_id", "revoked_at"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("report.id", ondelete="CASCADE"), index=True
    )
    clinician_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="CASCADE")
    )
    granted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = created_at()
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ClinicianNote(Base):
    """A doctor's note on a report shared with them; the family sees it beside the report."""

    __tablename__ = "clinician_note"

    id: Mapped[uuid.UUID] = uuid_pk()
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("report.id", ondelete="CASCADE"), index=True
    )
    clinician_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="SET NULL")
    )
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at()
