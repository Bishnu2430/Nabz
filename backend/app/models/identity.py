import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, ForeignKey, SmallInteger, Text
from sqlalchemy.dialects.postgresql import CITEXT, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at, pg_enum, uuid_pk
from app.models.enums import ConsentPurpose, Lang, Relationship, Sex, TokenPurpose, UserRole


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
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    totp_secret_enc: Mapped[str | None] = mapped_column(Text)  # Fernet-encrypted with SECRET_KEY
    totp_enabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_logins: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserSession(Base):
    """Server-side session. The cookie holds a random token; only its SHA-256 is stored."""

    __tablename__ = "user_session"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(Text, unique=True)
    csrf_token: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at()
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_agent: Mapped[str | None] = mapped_column(Text)


class AuthToken(Base):
    """Single-use email token (verify email, reset password). Only its SHA-256 is stored."""

    __tablename__ = "auth_token"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="CASCADE"), index=True
    )
    purpose: Mapped[TokenPurpose] = mapped_column(pg_enum(TokenPurpose, "token_purpose"))
    token_hash: Mapped[str] = mapped_column(Text, unique=True)
    created_at: Mapped[datetime] = created_at()
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


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
    # For a person under 18: when the account holder confirmed being their parent or lawful guardian (FR-05)
    guardian_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # What the family typed for the emergency card: blood group, allergies, conditions, medicines, contacts.
    emergency: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    # The person's own targets for home readings, by kind: {"bp": {"high": 130, "high2": 80}, ...}
    reading_targets: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
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
