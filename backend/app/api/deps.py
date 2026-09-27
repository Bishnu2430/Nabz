"""Request dependencies: database session, current user, storage."""

from __future__ import annotations

import uuid
from collections.abc import Iterator

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.security import UNUSABLE_PASSWORD_HASH
from app.db import SessionLocal
from app.models import AppUser, Profile, Report
from app.storage import StorageBackend, default_storage

DEV_EMAIL = "dev@nabz.local"


def get_sessionmaker() -> sessionmaker[Session]:
    return SessionLocal


def get_session(factory: sessionmaker[Session] = Depends(get_sessionmaker)) -> Iterator[Session]:  # noqa: B008
    with factory() as session:
        yield session


def get_storage() -> StorageBackend:
    return default_storage()


def current_user(session: Session = Depends(get_session)) -> AppUser:  # noqa: B008
    """Development stand-in for authentication (replaced by real sessions in Sprint 6)."""
    if not (settings.dev_auth and settings.app_env == "development"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign-in isn't available yet.")
    user = session.scalar(select(AppUser).where(AppUser.email == DEV_EMAIL))
    if user is None:
        user = AppUser(email=DEV_EMAIL, password_hash=UNUSABLE_PASSWORD_HASH)
        session.add(user)
        session.commit()
    return user


def owned_profile(session: Session, user: AppUser, profile_id: uuid.UUID) -> Profile:
    profile = session.get(Profile, profile_id)
    if profile is None or profile.owner_user_id != user.id or profile.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profile not found.")
    return profile


def owned_report(session: Session, user: AppUser, report_id: uuid.UUID) -> Report:
    """404 (not 403) for other people's reports, so their existence isn't revealed."""
    report = session.get(Report, report_id)
    if report is None or report.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found.")
    owned_profile(session, user, report.profile_id)
    return report
