"""Request dependencies: database session, current user (session cookie + CSRF), storage."""

from __future__ import annotations

import uuid
from collections.abc import Iterator

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db import SessionLocal
from app.models import AppUser, Profile, Report, UserSession
from app.models.enums import STAFF_ROLES, UserRole
from app.services.auth import session_user
from app.storage import StorageBackend, default_storage

# Behind HTTPS the cookie takes the __Host- prefix: Secure, path /, and never shared with another host (ASVS 3.3.1).
COOKIE = "__Host-nabz_session" if settings.cookie_secure else "nabz_session"
CSRF_HEADER = "X-CSRF-Token"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def get_sessionmaker() -> sessionmaker[Session]:
    return SessionLocal


def get_session(factory: sessionmaker[Session] = Depends(get_sessionmaker)) -> Iterator[Session]:  # noqa: B008
    with factory() as session:
        yield session


def get_storage() -> StorageBackend:
    return default_storage()


def current_session(request: Request,
                    session: Session = Depends(get_session)) -> tuple[UserSession, AppUser]:  # noqa: B008
    """The signed-in session. State-changing requests must also carry the session's CSRF token in a header."""
    found = session_user(session, request.cookies.get(COOKIE))
    if found is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please sign in.")
    row, user = found
    if request.method not in SAFE_METHODS and request.headers.get(CSRF_HEADER) != row.csrf_token:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "The request couldn't be verified. Reload the page.")
    return row, user


def current_user(found: tuple[UserSession, AppUser] = Depends(current_session)) -> AppUser:  # noqa: B008
    """The signed-in user, for everything outside /v1/auth. Staff must turn on two-step sign-in first."""
    _, user = found
    if user.role in STAFF_ROLES and user.totp_enabled_at is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            {"detail": "Turn on two-step sign-in to continue.", "setup": "totp"})
    return user


def require_roles(*roles: UserRole):
    """A dependency that lets only these roles through (FR-39); staff have already set up two-step sign-in."""
    def check(user: AppUser = Depends(current_user)) -> AppUser:  # noqa: B008
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, {"detail": "This area is for staff.", "code": "forbidden"})
        return user
    return check


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
