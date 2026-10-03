"""Accounts end to end with real cookies and CSRF: sign-up, verification, sign-in, lockout, reset, TOTP, staff rules,
idle expiry and deletion (FR-01, FR-33, docs/12 §3)."""

import re
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path

import pyotp
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.api import deps
from app.core.config import settings
from app.main import app
from app.models import AppUser, Profile, UserSession
from app.models.enums import UserRole
from app.services import auth as svc
from app.services import mail
from app.storage import LocalVolumeStorage

pytestmark = pytest.mark.db
PASSWORD = "correct horse battery"  # noqa: S105 - a test account
SAMPLE = Path(settings.data_dir) / "synthetic" / "samples" / "syn-2026-0002.pdf"


@pytest.fixture
def client(sessions: sessionmaker[Session], tmp_path: Path) -> Iterator[TestClient]:
    app.dependency_overrides[deps.get_sessionmaker] = lambda: sessions
    app.dependency_overrides[deps.get_storage] = lambda: LocalVolumeStorage(tmp_path / "uploads")
    mail.outbox.clear()
    svc.auth_limiter.reset()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def token_from_last_email(path: str) -> str:
    return re.search(rf"{path}\?token=([\w-]+)", mail.outbox[-1].get_content()).group(1)


def sign_up(client: TestClient, email: str = "asha@example.com", verify: bool = True) -> None:
    assert client.post("/v1/auth/register", json={"email": email, "password": PASSWORD}).status_code == 202
    if verify:
        token = token_from_last_email("/verify-email")
        assert client.post("/v1/auth/verify-email", json={"token": token}).status_code == 200


def sign_in(client: TestClient, email: str = "asha@example.com", password: str = PASSWORD, **extra) -> dict:
    r = client.post("/v1/auth/login", json={"email": email, "password": password, **extra})
    assert r.status_code == 200, r.text
    client.headers[deps.CSRF_HEADER] = r.json()["csrf_token"]
    return r.json()


def test_sign_up_verify_sign_in_and_csrf(client: TestClient) -> None:
    sign_up(client)
    assert "Confirm your email" in mail.outbox[0]["Subject"]
    me = sign_in(client)
    assert me["email_verified"] and me["role"] == "user" and client.cookies.get(deps.COOKIE)
    assert client.get("/v1/auth/me").json()["email"] == "asha@example.com"

    body = {"display_name": "Asha", "consent_processing": True}
    csrf = client.headers.pop(deps.CSRF_HEADER)
    assert client.post("/v1/profiles", json=body).status_code == 403  # no CSRF header
    client.headers[deps.CSRF_HEADER] = csrf
    assert client.post("/v1/profiles", json=body).status_code == 201


def test_the_same_answer_for_a_taken_email_and_no_second_account(client: TestClient, sessions) -> None:
    sign_up(client)
    r = client.post("/v1/auth/register", json={"email": "ASHA@example.com", "password": "another password 1"})
    assert r.status_code == 202 and "already has one" in mail.outbox[-1].get_content()
    with sessions() as s:
        assert len(s.scalars(select(AppUser)).all()) == 1


@pytest.mark.parametrize(("password", "status"), [("short", 422), ("aaaaaaaaaaaa", 422), ("asha-and-more-words", 422)])
def test_weak_passwords_are_refused(client: TestClient, password: str, status: int) -> None:
    r = client.post("/v1/auth/register", json={"email": "asha@example.com", "password": password})
    assert r.status_code == status and r.json()["code"] == "password"


def test_wrong_passwords_lock_the_account_and_errors_stay_generic(client: TestClient) -> None:
    sign_up(client)
    unknown = client.post("/v1/auth/login", json={"email": "nobody@example.com", "password": PASSWORD})
    wrong = client.post("/v1/auth/login", json={"email": "asha@example.com", "password": "wrong password!"})
    assert unknown.status_code == wrong.status_code == 401 and unknown.json()["detail"] == wrong.json()["detail"]
    for _ in range(4):
        client.post("/v1/auth/login", json={"email": "asha@example.com", "password": "wrong password!"})
    locked = client.post("/v1/auth/login", json={"email": "asha@example.com", "password": PASSWORD})
    assert locked.status_code == 429 and locked.json()["code"] == "locked"


def test_upload_needs_a_confirmed_email(client: TestClient) -> None:
    sign_up(client, verify=False)
    sign_in(client)
    pid = client.post("/v1/profiles", json={"display_name": "Asha", "consent_processing": True}).json()["id"]
    r = client.post(f"/v1/profiles/{pid}/reports", files={"file": ("r.pdf", SAMPLE.read_bytes(), "application/pdf")})
    assert r.status_code == 403 and r.json()["code"] == "verify_email"


def test_password_reset_is_single_use_and_signs_out_everywhere(client: TestClient) -> None:
    sign_up(client)
    sign_in(client)
    assert client.post("/v1/auth/forgot-password", json={"email": "nobody@example.com"}).status_code == 202
    n = len(mail.outbox)
    client.post("/v1/auth/forgot-password", json={"email": "asha@example.com"})
    assert len(mail.outbox) == n + 1  # unknown emails get the same answer and no email
    token = token_from_last_email("/reset-password")
    new = "a brand new passphrase"
    assert client.post("/v1/auth/reset-password", json={"token": token, "password": new}).status_code == 200
    assert client.get("/v1/auth/me").status_code == 401  # the old session is gone
    assert client.post("/v1/auth/reset-password", json={"token": token, "password": new}).status_code == 400
    sign_in(client, password=new)


def test_sign_out_and_sign_out_everywhere(client: TestClient, sessions) -> None:
    sign_up(client)
    sign_in(client)
    other = TestClient(app)
    other.post("/v1/auth/login", json={"email": "asha@example.com", "password": PASSWORD})
    assert other.get("/v1/auth/me").status_code == 200
    assert client.post("/v1/auth/logout-all").status_code == 204
    assert other.get("/v1/auth/me").status_code == 401 and client.get("/v1/auth/me").status_code == 401


def test_sessions_expire_when_idle(client: TestClient, sessions) -> None:
    sign_up(client)
    sign_in(client)
    with sessions.begin() as s:
        for row in s.scalars(select(UserSession)):
            row.last_seen_at -= timedelta(days=settings.session_idle_days + 1)
    assert client.get("/v1/auth/me").status_code == 401


def test_two_step_sign_in(client: TestClient) -> None:
    sign_up(client)
    sign_in(client)
    setup = client.post("/v1/auth/totp/setup").json()
    assert setup["uri"].startswith("otpauth://totp/Nabz:") and setup["qr_svg"].startswith("data:image/svg+xml")
    assert client.post("/v1/auth/totp/enable", json={"code": "000000"}).status_code == 400
    code = pyotp.TOTP(setup["secret"]).now()
    assert client.post("/v1/auth/totp/enable", json={"code": code}).json()["totp_enabled"] is True
    client.post("/v1/auth/logout")
    r = client.post("/v1/auth/login", json={"email": "asha@example.com", "password": PASSWORD})
    assert r.status_code == 401 and r.json()["code"] == "totp_required"
    sign_in(client, totp_code=pyotp.TOTP(setup["secret"]).now())


def test_staff_must_turn_on_two_step_sign_in(client: TestClient, sessions) -> None:
    sign_up(client, email="admin@example.com")
    with sessions.begin() as s:
        s.scalar(select(AppUser)).role = UserRole.ADMIN
    me = sign_in(client, email="admin@example.com")
    assert me["totp_required"] is True
    r = client.get("/v1/profiles")
    assert r.status_code == 403 and r.json()["setup"] == "totp"
    secret = client.post("/v1/auth/totp/setup").json()["secret"]
    client.post("/v1/auth/totp/enable", json={"code": pyotp.TOTP(secret).now()})
    assert client.get("/v1/profiles").status_code == 200
    assert client.post("/v1/auth/totp/disable", json={"password": PASSWORD}).status_code == 409


def test_deleting_the_account_removes_everything(client: TestClient, sessions) -> None:
    sign_up(client)
    sign_in(client)
    client.post("/v1/profiles", json={"display_name": "Asha", "consent_processing": True})
    assert client.request("DELETE", "/v1/auth/account", json={"password": "wrong password!"}).status_code == 400
    assert client.request("DELETE", "/v1/auth/account", json={"password": PASSWORD}).status_code == 204
    with sessions() as s:
        assert s.scalars(select(AppUser)).all() == [] and s.scalars(select(Profile)).all() == []
    assert client.post("/v1/auth/login", json={"email": "asha@example.com", "password": PASSWORD}).status_code == 401


def test_one_of_the_most_used_passwords_is_refused_in_any_case(client: TestClient) -> None:
    """ASVS 5.0 6.2.4: the NCSC's most used passwords of policy length are refused, whatever their case."""
    r = client.post("/v1/auth/register", json={"email": "asha@example.com", "password": "QwertyUIOP"})
    assert r.status_code == 422 and r.json()["code"] == "password_common"
    assert client.post("/v1/auth/register", json={"email": "asha@example.com", "password": PASSWORD}).status_code == 202


def test_every_response_carries_the_security_headers(client: TestClient, monkeypatch) -> None:
    ok, problem = client.get("/v1/catalogue/tests"), client.get("/v1/auth/me")
    for r in (ok, problem):
        assert r.headers["x-content-type-options"] == "nosniff" and r.headers["x-frame-options"] == "DENY"
        assert r.headers["referrer-policy"] == "no-referrer"
        assert r.headers["content-security-policy"] == "default-src 'none'; frame-ancestors 'none'"
        assert r.headers["content-type"].endswith("charset=utf-8")
    assert "strict-transport-security" not in ok.headers  # plain HTTP in development
    monkeypatch.setattr(settings, "cookie_secure", True)
    assert client.get("/v1/catalogue/tests").headers["strict-transport-security"].startswith("max-age=31536000")


def test_signing_in_again_ends_the_session_the_browser_had(client: TestClient, sessions) -> None:
    sign_up(client)
    sign_in(client)
    first = client.cookies.get(deps.COOKIE)
    sign_in(client)
    assert client.cookies.get(deps.COOKIE) != first
    with sessions() as s:
        rows = s.scalars(select(UserSession).order_by(UserSession.created_at)).all()
        assert [r.revoked_at is not None for r in rows] == [True, False]


def test_secrets_at_rest_use_aes_gcm_and_older_values_still_read() -> None:
    from cryptography.fernet import Fernet

    from app.core import security

    blob = security.encrypt("JBSWY3DPEHPK3PXP")
    assert blob.startswith(security.GCM_PREFIX) and security.decrypt(blob) == "JBSWY3DPEHPK3PXP"
    assert security.encrypt("JBSWY3DPEHPK3PXP") != blob  # a fresh nonce every time
    assert security.decrypt(blob[:-4] + "AAAA") is None  # tampering is caught
    legacy = security._fernet().encrypt(b"JBSWY3DPEHPK3PXP").decode()
    assert isinstance(security._fernet(), Fernet) and security.decrypt(legacy) == "JBSWY3DPEHPK3PXP"
