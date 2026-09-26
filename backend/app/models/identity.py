import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import CITEXT, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at, pg_enum, uuid_pk
from app.models.enums import ConsentPurpose, Lang, Relationship, Sex, UserRole


class AppUser(Base):
    """Account holder and login identity."""

    __tablename__ = "app_user"

    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(CITEXT, unique=True)
    phone: Mapped[str | None] = mapped_column(Text)
    password_hash: Mapped[str] = mapped_column(Text)
    preferred_language: Mapped[Lang] = mapped_column(pg_enum(Lang, "lang"), default=Lang.EN)
    role: Mapped[UserRole] = mapped_column(pg_enum(UserRole, "user_role"), default=UserRole.USER)
    created_at: Mapped[datetime] = created_at()
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Profile(Base):
    """A person whose reports are managed by an account (self, parent, child…)."""

    __tablename__ = "profile"

    id: Mapped[uuid.UUID] = uuid_pk()
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="CASCADE"), index=True
    )
    display_name: Mapped[str] = mapped_column(Text)
    sex: Mapped[Sex] = mapped_column(pg_enum(Sex, "sex"), default=Sex.UNKNOWN)
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    relationship: Mapped[Relationship] = mapped_column(
        pg_enum(Relationship, "relationship"), default=Relationship.SELF
    )
    preferred_language: Mapped[Lang] = mapped_column(pg_enum(Lang, "lang"), default=Lang.EN)
    created_at: Mapped[datetime] = created_at()
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Consent(Base):
    """Per-profile, per-purpose consent with the policy version it was given under."""

    __tablename__ = "consent"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="CASCADE"))
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profile.id", ondelete="CASCADE"), index=True
    )
    purpose: Mapped[ConsentPurpose] = mapped_column(pg_enum(ConsentPurpose, "consent_purpose"))
    policy_version: Mapped[str] = mapped_column(Text)
    granted_at: Mapped[datetime] = created_at()
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
