"""Things a family keeps beside the lab reports: reminders they set and readings they take at home."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, SmallInteger, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at, pg_enum, uuid_pk
from app.models.enums import ReadingKind


class Reminder(Base):
    """A date the family set for themselves ("repeat HbA1c in 3 months, as the doctor said"). Nabz never
    proposes the interval."""

    __tablename__ = "reminder"
    __table_args__ = (Index("ix_reminder_due", "due_on", postgresql_where=text("done_at IS NULL")),)

    id: Mapped[uuid.UUID] = uuid_pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profile.id", ondelete="CASCADE"), index=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(Text)
    test_code: Mapped[str | None] = mapped_column(Text)  # the catalogue test it is about, if any
    due_on: Mapped[date] = mapped_column(Date)
    repeat_months: Mapped[int | None] = mapped_column(SmallInteger)
    note: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # the email went out
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at()


class HomeReading(Base):
    __tablename__ = "home_reading"
    __table_args__ = (Index("ix_home_reading_profile_kind_time", "profile_id", "kind", text("taken_at DESC")),)

    id: Mapped[uuid.UUID] = uuid_pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profile.id", ondelete="CASCADE"))
    kind: Mapped[ReadingKind] = mapped_column(pg_enum(ReadingKind, "reading_kind"))
    value: Mapped[Decimal] = mapped_column(Numeric)
    value2: Mapped[Decimal | None] = mapped_column(Numeric)  # diastolic, for blood pressure
    context: Mapped[str | None] = mapped_column(Text)  # "fasting", "after_meal", "morning", "evening"
    note: Mapped[str | None] = mapped_column(Text)
    taken_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at()
