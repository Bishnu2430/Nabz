"""Accounts: sign-up, email verification, sign-in and out, password reset, two-step sign-in, deletion (FR-01, FR-33)."""

from __future__ import annotations

import base64
import io

import segno
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import COOKIE, current_session, get_session, get_storage
from app.core import security
from app.core.config import settings
from app.models import AppUser, UserSession
from app.models.enums import STAFF_ROLES
from app.schemas import (
    ChangePasswordIn,
    CodeIn,
    EmailIn,
    LoginIn,
    MeOut,
    MePatch,
    PasswordIn,
    RegisterIn,
    ResetIn,
    TokenIn,
    TotpSetupOut,
)
from app.services import audit, data_rights
from app.services import auth as svc
from app.storage import StorageBackend

router = APIRouter(prefix="/v1/auth", tags=["auth"])
Found = tuple[UserSession, AppUser]


def _me(row: UserSession, user: AppUser) -> MeOut:
    return MeOut(id=user.id, email=user.email, role=user.role.value, preferred_language=user.preferred_language,
                 email_verified=user.email_verified_at is not None, totp_enabled=user.totp_enabled_at is not None,
                 totp_required=user.role in STAFF_ROLES and user.totp_enabled_at is None, csrf_token=row.csrf_token)


def _limit(request: Request) -> None:
    if not svc.auth_limiter.allow(request.client.host if request.client else "unknown"):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts. Wait a minute and try again.")


def _raise(exc: svc.AuthError) -> None:
    raise HTTPException(exc.status, {"detail": exc.message, "code": exc.code}) from exc


def _set_cookie(response: Response, token: str) -> None:
    response.set_cookie(COOKIE, token, httponly=True, secure=settings.cookie_secure, samesite="strict", path="/",
                        max_age=settings.session_idle_days * 86400)


@router.post("/register", status_code=status.HTTP_202_ACCEPTED)
def register(body: RegisterIn, request: Request, session: Session = Depends(get_session)):  # noqa: B008
    """Always the same answer, whether or not the email is registered (the owner gets an email either way)."""
    _limit(request)
    try:
        user = svc.register(session, body.email, body.password, body.preferred_language)
    except svc.AuthError as exc:
        _raise(exc)
    if user is not None:
        audit.record(session, user.id, "account.register", "app_user", user.id)
    session.commit()
    return {"detail": "Check your email for a link to confirm your address."}


@router.post("/verify-email")
def verify_email(body: TokenIn, session: Session = Depends(get_session)):  # noqa: B008
    try:
        user = svc.verify_email(session, body.token)
    except svc.AuthError as exc:
        _raise(exc)
    audit.record(session, user.id, "account.verify_email", "app_user", user.id)
    session.commit()
    return {"detail": "Your email is confirmed."}


@router.post("/resend-verification", status_code=status.HTTP_202_ACCEPTED)
def resend_verification(request: Request, found: Found = Depends(current_session),  # noqa: B008
                        session: Session = Depends(get_session)):  # noqa: B008
    _limit(request)
    user = session.get(AppUser, found[1].id)
    if user.email_verified_at is None:
        svc.send_verification(session, user)
        session.commit()
    return {"detail": "We've sent the link again."}


@router.post("/login", response_model=MeOut)
def login(body: LoginIn, request: Request, response: Response,
          session: Session = Depends(get_session)):  # noqa: B008
    _limit(request)
    try:
        user = svc.authenticate(session, body.email, body.password, body.totp_code)
    except svc.AuthError as exc:
        session.commit()  # keep the failed-attempt count and any lockout
        _raise(exc)
    new = svc.create_session(session, user, request.headers.get("user-agent"))
    audit.record(session, user.id, "account.login", "app_user", user.id)
    session.commit()
    _set_cookie(response, new.token)
    return _me(new.row, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, found: Found = Depends(current_session),  # noqa: B008
           session: Session = Depends(get_session)):  # noqa: B008
    row = session.get(UserSession, found[0].id)
    row.revoked_at = svc.now()
    session.commit()
    response.delete_cookie(COOKIE, path="/")


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
def logout_all(response: Response, found: Found = Depends(current_session),  # noqa: B008
               session: Session = Depends(get_session)):  # noqa: B008
    svc.revoke_all(session, found[1].id)
    audit.record(session, found[1].id, "account.logout_all", "app_user", found[1].id)
    session.commit()
    response.delete_cookie(COOKIE, path="/")


@router.get("/me", response_model=MeOut)
def me(found: Found = Depends(current_session)):  # noqa: B008
    return _me(*found)


@router.patch("/me", response_model=MeOut)
def update_me(body: MePatch, found: Found = Depends(current_session),  # noqa: B008
              session: Session = Depends(get_session)):  # noqa: B008
    user = session.get(AppUser, found[1].id)
    user.preferred_language = body.preferred_language
    session.commit()
    return _me(found[0], user)


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
def forgot_password(body: EmailIn, request: Request, session: Session = Depends(get_session)):  # noqa: B008
    _limit(request)
    svc.request_reset(session, body.email)
    session.commit()
    return {"detail": "If that email has an account, we've sent a link to reset the password."}


@router.post("/reset-password")
def reset_password(body: ResetIn, session: Session = Depends(get_session)):  # noqa: B008
    try:
        user = svc.reset_password(session, body.token, body.password)
    except svc.AuthError as exc:
        _raise(exc)
    audit.record(session, user.id, "account.reset_password", "app_user", user.id)
    session.commit()
    return {"detail": "Your password is changed. Sign in with the new one."}


@router.post("/change-password")
def change_password(body: ChangePasswordIn, found: Found = Depends(current_session),  # noqa: B008
                    session: Session = Depends(get_session)):  # noqa: B008
    user = session.get(AppUser, found[1].id)
    try:
        svc.change_password(session, user, body.current_password, body.new_password, keep=found[0].id)
    except svc.AuthError as exc:
        _raise(exc)
    audit.record(session, user.id, "account.change_password", "app_user", user.id)
    session.commit()
    return {"detail": "Your password is changed. Other devices have been signed out."}


@router.post("/totp/setup", response_model=TotpSetupOut)
def totp_setup(found: Found = Depends(current_session), session: Session = Depends(get_session)):  # noqa: B008
    user = session.get(AppUser, found[1].id)
    try:
        secret, uri = svc.totp_setup(user)
    except svc.AuthError as exc:
        _raise(exc)
    session.commit()
    buf = io.BytesIO()
    segno.make(uri, error="m").save(buf, kind="svg", scale=5, border=2, dark="#1f1d1b", light="#fbf8f2")
    return TotpSetupOut(secret=secret, uri=uri,
                        qr_svg="data:image/svg+xml;base64," + base64.b64encode(buf.getvalue()).decode())


@router.post("/totp/enable", response_model=MeOut)
def totp_enable(body: CodeIn, found: Found = Depends(current_session),  # noqa: B008
                session: Session = Depends(get_session)):  # noqa: B008
    user = session.get(AppUser, found[1].id)
    try:
        svc.totp_enable(user, body.code)
    except svc.AuthError as exc:
        _raise(exc)
    audit.record(session, user.id, "account.totp_enable", "app_user", user.id)
    session.commit()
    return _me(found[0], user)


@router.post("/totp/disable", response_model=MeOut)
def totp_disable(body: PasswordIn, found: Found = Depends(current_session),  # noqa: B008
                 session: Session = Depends(get_session)):  # noqa: B008
    user = session.get(AppUser, found[1].id)
    try:
        svc.totp_disable(user, body.password)
    except svc.AuthError as exc:
        _raise(exc)
    audit.record(session, user.id, "account.totp_disable", "app_user", user.id)
    session.commit()
    return _me(found[0], user)


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(body: PasswordIn, response: Response, found: Found = Depends(current_session),  # noqa: B008
                   session: Session = Depends(get_session),  # noqa: B008
                   storage: StorageBackend = Depends(get_storage)):  # noqa: B008
    """Hard delete (FR-33): the account, every profile and report, and the stored files. The audit trail keeps
    the event without the person (its actor becomes empty)."""
    user = session.get(AppUser, found[1].id)
    if not security.verify_password(user.password_hash, body.password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"detail": "Your password is wrong.",
                                                          "code": "current_password"})
    keys = (data_rights.stored_keys(session, data_rights.account_reports(user.id))
            + data_rights.record_keys(session, data_rights.account_records(user.id)))
    audit.record(session, None, "account.delete", "app_user", user.id, files=len(keys))
    session.delete(user)
    session.commit()
    data_rights.remove_objects(storage, keys)
    response.delete_cookie(COOKIE, path="/")
