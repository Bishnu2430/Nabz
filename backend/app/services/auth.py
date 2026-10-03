"""Accounts, sessions and email tokens (FR-01, docs/12 §3).

- Passwords: Argon2id; at least 10 characters.
- Sign-in: generic errors that never say whether an email is registered. Five failed attempts lock the account for
  15 minutes; a per-IP limiter also slows guessing.
- Sessions: a random token in an HttpOnly cookie, only its SHA-256 stored; idle expiry 14 days (staff: 1 day);
  revocable one by one or all at once. Each session has a CSRF token for state-changing requests.
- Email tokens (verify, reset): single-use, hashed at rest, 24 hours and 30 minutes.
- TOTP: required for staff (reviewer, admin), optional otherwise; the secret is encrypted with SECRET_KEY.
"""

from __future__ import annotations

import re
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import settings
from app.models import AppUser, AuthToken, UserSession
from app.models.enums import STAFF_ROLES, Lang, TokenPurpose
from app.services import mail

VERIFY_TTL = timedelta(hours=24)
RESET_TTL = timedelta(minutes=30)
LOCK_AFTER = 5
LOCK_FOR = timedelta(minutes=15)
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# Verifying against a real hash when the email is unknown keeps the response time the same.
_DUMMY_HASH = security.hash_password("not-a-real-password-just-for-timing")


class AuthError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


INVALID = AuthError(401, "invalid", "The email or password is wrong.")


def now() -> datetime:
    return datetime.now(UTC)


def normalise_email(email: str) -> str:
    email = email.strip().lower()
    if not EMAIL.match(email) or len(email) > 254:
        raise AuthError(422, "email", "Enter a valid email address.")
    return email


def find_user(session: Session, email: str) -> AppUser | None:
    return session.scalar(select(AppUser).where(AppUser.email == email, AppUser.deleted_at.is_(None)))


# --- email tokens ------------------------------------------------------------------------------------------------


def issue_token(session: Session, user: AppUser, purpose: TokenPurpose, ttl: timedelta) -> str:
    token = security.new_token()
    session.add(AuthToken(user_id=user.id, purpose=purpose, token_hash=security.token_hash(token),
                          expires_at=now() + ttl))
    session.flush()
    return token


def use_token(session: Session, token: str, purpose: TokenPurpose) -> AppUser:
    t = session.scalar(select(AuthToken).where(AuthToken.token_hash == security.token_hash(token),
                                               AuthToken.purpose == purpose).with_for_update())
    if t is None or t.used_at is not None or t.expires_at < now():
        raise AuthError(400, "token", "This link has expired or was already used. Ask for a new one.")
    t.used_at = now()
    user = session.get(AppUser, t.user_id)
    if user is None or user.deleted_at is not None:
        raise AuthError(400, "token", "This link has expired or was already used. Ask for a new one.")
    return user


def link(path: str, token: str) -> str:
    return f"{settings.app_base_url}{path}?token={token}"


# --- registration and verification -------------------------------------------------------------------------------


def register(session: Session, email: str, password: str, language: Lang) -> AppUser | None:
    """Create an unverified account and send the verification email. Returns None if the email is taken (the
    caller answers the same either way, and the owner gets a heads-up email instead)."""
    email = normalise_email(email)
    if problem := security.password_problem(password, email):
        raise AuthError(422, "password_common" if problem == security.COMMON else "password", problem)
    existing = find_user(session, email)
    if existing is not None:
        mail.send_template("exists", email, existing.preferred_language.value, f"{settings.app_base_url}/login")
        return None
    user = AppUser(email=email, password_hash=security.hash_password(password), preferred_language=language)
    session.add(user)
    session.flush()
    send_verification(session, user)
    return user


def send_verification(session: Session, user: AppUser) -> None:
    token = issue_token(session, user, TokenPurpose.VERIFY_EMAIL, VERIFY_TTL)
    mail.send_template("verify", user.email, user.preferred_language.value, link("/verify-email", token))


def verify_email(session: Session, token: str) -> AppUser:
    user = use_token(session, token, TokenPurpose.VERIFY_EMAIL)
    user.email_verified_at = user.email_verified_at or now()
    return user


# --- sign-in -----------------------------------------------------------------------------------------------------


def authenticate(session: Session, email: str, password: str, totp_code: str | None) -> AppUser:
    try:
        email = normalise_email(email)
    except AuthError:
        raise INVALID from None
    user = find_user(session, email)
    if user is None:
        security.verify_password(_DUMMY_HASH, password)
        raise INVALID
    if user.locked_until and user.locked_until > now():
        raise AuthError(429, "locked", "Too many attempts. Try again in 15 minutes, or reset your password.")
    if not security.verify_password(user.password_hash, password):
        _failed(user)
        raise INVALID
    if user.totp_enabled_at:
        if not totp_code:
            raise AuthError(401, "totp_required", "Enter the 6-digit code from your authenticator app.")
        secret = security.decrypt(user.totp_secret_enc or "")
        if not secret or not security.verify_totp(secret, totp_code):
            _failed(user)
            raise AuthError(401, "totp_invalid", "That code didn't work. Check the time on your phone and try again.")
    user.failed_logins = 0
    user.locked_until = None
    user.last_login_at = now()
    if security.needs_rehash(user.password_hash):
        user.password_hash = security.hash_password(password)
    return user


def _failed(user: AppUser) -> None:
    user.failed_logins = (user.failed_logins or 0) + 1
    if user.failed_logins >= LOCK_AFTER:
        user.locked_until = now() + LOCK_FOR
        user.failed_logins = 0


# --- sessions ----------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class NewSession:
    token: str
    csrf_token: str
    row: UserSession


def create_session(session: Session, user: AppUser, user_agent: str | None) -> NewSession:
    token, csrf = security.new_token(), security.new_token()
    row = UserSession(user_id=user.id, token_hash=security.token_hash(token), csrf_token=csrf,
                      last_seen_at=now(), user_agent=(user_agent or "")[:300] or None)
    session.add(row)
    session.flush()
    return NewSession(token, csrf, row)


def end_session(session: Session, token: str | None) -> None:
    """Revoke the session a token belongs to, if any (signing in ends the one the browser had, ASVS 7.2.4)."""
    if token:
        row = session.scalar(select(UserSession).where(UserSession.token_hash == security.token_hash(token),
                                                       UserSession.revoked_at.is_(None)))
        if row is not None:
            row.revoked_at = now()


def idle_limit(user: AppUser) -> timedelta:
    if user.role in STAFF_ROLES:
        return timedelta(hours=settings.staff_session_hours)
    return timedelta(days=settings.session_idle_days)


def session_user(session: Session, token: str | None) -> tuple[UserSession, AppUser] | None:
    if not token:
        return None
    row = session.scalar(select(UserSession).where(UserSession.token_hash == security.token_hash(token)))
    if row is None or row.revoked_at is not None:
        return None
    user = session.get(AppUser, row.user_id)
    if user is None or user.deleted_at is not None or row.last_seen_at + idle_limit(user) < now():
        return None
    if now() - row.last_seen_at > timedelta(minutes=5):  # don't write on every request
        row.last_seen_at = now()
        session.commit()
    return row, user


def revoke_all(session: Session, user_id: uuid.UUID, keep: uuid.UUID | None = None) -> int:
    q = update(UserSession).where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
    if keep is not None:
        q = q.where(UserSession.id != keep)
    return session.execute(q.values(revoked_at=now())).rowcount or 0


# --- passwords ---------------------------------------------------------------------------------------------------


def request_reset(session: Session, email: str) -> None:
    try:
        user = find_user(session, normalise_email(email))
    except AuthError:
        return
    if user is not None:
        token = issue_token(session, user, TokenPurpose.RESET_PASSWORD, RESET_TTL)
        mail.send_template("reset", user.email, user.preferred_language.value, link("/reset-password", token))


def reset_password(session: Session, token: str, password: str) -> AppUser:
    user = use_token(session, token, TokenPurpose.RESET_PASSWORD)
    if problem := security.password_problem(password, user.email):
        raise AuthError(422, "password_common" if problem == security.COMMON else "password", problem)
    user.password_hash = security.hash_password(password)
    user.failed_logins, user.locked_until = 0, None
    user.email_verified_at = user.email_verified_at or now()  # the reset link proves the email
    revoke_all(session, user.id)
    return user


def change_password(session: Session, user: AppUser, current: str, new: str, keep: uuid.UUID) -> None:
    if not security.verify_password(user.password_hash, current):
        raise AuthError(400, "current_password", "Your current password is wrong.")
    if problem := security.password_problem(new, user.email):
        raise AuthError(422, "password_common" if problem == security.COMMON else "password", problem)
    user.password_hash = security.hash_password(new)
    revoke_all(session, user.id, keep=keep)


# --- TOTP --------------------------------------------------------------------------------------------------------


def totp_setup(user: AppUser) -> tuple[str, str]:
    """A new secret (not active until confirmed with a code) and its otpauth:// URI."""
    if user.totp_enabled_at:
        raise AuthError(409, "totp_enabled", "Two-step sign-in is already on.")
    secret = security.new_totp_secret()
    user.totp_secret_enc = security.encrypt(secret)
    return secret, security.totp_uri(secret, user.email)


def totp_enable(user: AppUser, code: str) -> None:
    secret = security.decrypt(user.totp_secret_enc or "")
    if not secret:
        raise AuthError(409, "totp_setup", "Start the set-up again.")
    if not security.verify_totp(secret, code):
        raise AuthError(400, "totp_invalid", "That code didn't work. Check the time on your phone and try again.")
    user.totp_enabled_at = now()


def totp_disable(user: AppUser, password: str) -> None:
    if user.role in STAFF_ROLES:
        raise AuthError(409, "totp_required", "Two-step sign-in is required for staff accounts.")
    if not security.verify_password(user.password_hash, password):
        raise AuthError(400, "current_password", "Your password is wrong.")
    user.totp_secret_enc = None
    user.totp_enabled_at = None


# --- rate limiting -----------------------------------------------------------------------------------------------


class RateLimiter:
    """Sliding-window limit per key, in memory: enough for one API process (the prototype's deployment)."""

    def __init__(self, limit: int, window_seconds: float):
        self.limit, self.window = limit, window_seconds
        self.hits: dict[str, deque[float]] = defaultdict(deque)
        self.lock = threading.Lock()

    def allow(self, key: str) -> bool:
        t = time.monotonic()
        with self.lock:
            q = self.hits[key]
            while q and q[0] <= t - self.window:
                q.popleft()
            if len(q) >= self.limit:
                return False
            q.append(t)
            return True

    def reset(self) -> None:
        with self.lock:
            self.hits.clear()


auth_limiter = RateLimiter(limit=20, window_seconds=60)  # sign-in, sign-up and reset requests per IP
