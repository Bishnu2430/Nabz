"""Outgoing email over SMTP: Mailpit in development, a mail service over TLS with a login when hosted (docs/14)."""

import smtplib

import pytest

from app.core.config import settings
from app.services import mail


class FakeSMTP:
    instances: list["FakeSMTP"] = []

    def __init__(self, host: str, port: int, timeout: float, context=None, fail_login: bool = False):
        self.host, self.port, self.calls, self.sent, self.closed = host, port, [], [], False
        self.fail_login = fail_login
        FakeSMTP.instances.append(self)

    def starttls(self, context=None):
        self.calls.append("starttls")

    def login(self, user: str, password: str):
        self.calls.append(("login", user))
        if self.fail_login:
            raise smtplib.SMTPAuthenticationError(535, b"bad login")

    def send_message(self, msg):
        self.sent.append(msg)

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


@pytest.fixture
def smtp(monkeypatch: pytest.MonkeyPatch):
    FakeSMTP.instances.clear()
    monkeypatch.setattr(settings, "mail_backend", "smtp")
    monkeypatch.setattr(smtplib, "SMTP", lambda *a, **k: FakeSMTP(*a, **k))
    monkeypatch.setattr(smtplib, "SMTP_SSL", lambda *a, **k: FakeSMTP(*a, **k, fail_login=False))
    return monkeypatch


def test_mailpit_needs_no_login(smtp) -> None:
    smtp.setattr(settings, "smtp_security", "none")
    smtp.setattr(settings, "smtp_username", "")
    mail.send("a@example.com", "Hello", "Body")
    (conn,) = FakeSMTP.instances
    assert conn.calls == [] and len(conn.sent) == 1 and conn.closed


@pytest.mark.parametrize("security", ["starttls", "ssl"])
def test_a_mail_service_gets_tls_and_the_login(smtp, security: str) -> None:
    smtp.setattr(settings, "smtp_security", security)
    smtp.setattr(settings, "smtp_username", "apikey")
    smtp.setattr(settings, "smtp_password", "secret")
    mail.send("a@example.com", "Hello", "Body")
    (conn,) = FakeSMTP.instances
    expected = ["starttls", ("login", "apikey")] if security == "starttls" else [("login", "apikey")]
    assert conn.calls == expected and len(conn.sent) == 1


def test_a_refused_login_does_not_break_sign_up(smtp) -> None:
    smtp.setattr(settings, "smtp_security", "starttls")
    smtp.setattr(settings, "smtp_username", "apikey")
    smtp.setattr(smtplib, "SMTP", lambda *a, **k: FakeSMTP(*a, **k, fail_login=True))
    mail.send("a@example.com", "Hello", "Body")  # logged, not raised
    (conn,) = FakeSMTP.instances
    assert conn.sent == [] and conn.closed
