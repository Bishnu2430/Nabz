"""Reminders, home readings and the emergency card: the family's own entries, private, exported and erased."""

from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.api import deps
from app.core.security import UNUSABLE_PASSWORD_HASH
from app.main import app
from app.models import AppUser, HomeReading, Reminder
from app.services import mail, reminders
from app.storage import LocalVolumeStorage

pytestmark = pytest.mark.db


@pytest.fixture
def as_user(sessions: sessionmaker[Session]):
    users: dict[str, AppUser] = {}

    def switch(name: str) -> AppUser:
        if name not in users:
            with sessions.begin() as s:
                u = AppUser(email=f"{name}@nabz.local", password_hash=UNUSABLE_PASSWORD_HASH,
                            email_verified_at=datetime.now(UTC))
                s.add(u)
            users[name] = u
        app.dependency_overrides[deps.current_user] = lambda: users[name]
        return users[name]

    switch("alice")
    return switch


@pytest.fixture
def client(sessions: sessionmaker[Session], tmp_path: Path, as_user) -> Iterator[TestClient]:
    app.dependency_overrides[deps.get_sessionmaker] = lambda: sessions
    app.dependency_overrides[deps.get_storage] = lambda: LocalVolumeStorage(tmp_path / "uploads")
    mail.outbox.clear()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _profile(client: TestClient) -> str:
    return client.post("/v1/profiles", json={"display_name": "Ramesh", "sex": "male", "date_of_birth": "1968-03-14",
                                             "relationship": "spouse", "consent_processing": True}).json()["id"]


def test_add_months_keeps_the_day_or_the_months_last() -> None:
    assert reminders.add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert reminders.add_months(date(2026, 11, 19), 3) == date(2027, 2, 19)
    assert reminders.add_months(date(2024, 2, 29), 12) == date(2025, 2, 28)


def test_a_reminder_repeats_emails_once_and_exports_to_a_calendar(client: TestClient, as_user, sessions) -> None:
    pid = _profile(client)
    made = client.post(f"/v1/profiles/{pid}/reminders", json={
        "title": "Repeat HbA1c", "due_on": "2026-11-19", "test_code": "hba1c", "repeat_months": 3, "note": "Fasting"})
    assert made.status_code == 201
    rid = made.json()["id"]
    assert client.post(f"/v1/profiles/{pid}/reminders",
                       json={"title": "x", "due_on": "2026-11-19", "test_code": "no_such"}).status_code == 422

    ics = client.get(f"/v1/reminders/{rid}/calendar.ics")
    assert ics.headers["content-type"].startswith("text/calendar")
    assert "DTSTART;VALUE=DATE:20261119" in ics.text and "RRULE:FREQ=MONTHLY;INTERVAL=3" in ics.text
    assert "SUMMARY:Repeat HbA1c (Ramesh)" in ics.text

    # not due yet: nothing goes out; on its date one email goes out, once
    with sessions.begin() as s:
        assert reminders.send_due(s, today=date(2026, 11, 18)) == 0
    with sessions.begin() as s:
        assert reminders.send_due(s, today=date(2026, 11, 19)) == 1
    with sessions.begin() as s:
        assert reminders.send_due(s, today=date(2026, 11, 20)) == 0
    assert len(mail.outbox) == 1 and mail.outbox[0]["Subject"] == "Nabz reminder: Repeat HbA1c"
    body = mail.outbox[0].get_content()
    assert "for Ramesh" in body and "Due: 19 Nov 2026" in body and "Nabz doesn't decide" in body

    # "send now" works at any time; done leaves the next occurrence three months on
    assert client.post(f"/v1/reminders/{rid}/send").json()["sent_at"] and len(mail.outbox) == 2
    assert client.patch(f"/v1/reminders/{rid}", json={"done": True}).json()["done_at"]
    listed = client.get(f"/v1/profiles/{pid}/reminders").json()
    assert [(r["due_on"], r["done_at"] is not None) for r in listed] == [("2027-02-19", False), ("2026-11-19", True)]

    as_user("mallory")
    assert client.get(f"/v1/profiles/{pid}/reminders").status_code == 404
    assert client.delete(f"/v1/reminders/{rid}").status_code == 404
    assert client.get(f"/v1/reminders/{rid}/calendar.ics").status_code == 404
    as_user("alice")
    assert client.delete(f"/v1/reminders/{rid}").status_code == 204


def test_home_readings_are_checked_charted_against_the_persons_own_target(client: TestClient, as_user) -> None:
    pid = _profile(client)
    ok = client.post(f"/v1/profiles/{pid}/readings", json={"kind": "bp", "value": 148, "value2": 92,
                                                           "context": "morning"})
    assert ok.status_code == 201 and ok.json()["value2"] == "92"
    # typing mistakes are refused with a plain reason
    for bad in ({"kind": "bp", "value": 128}, {"kind": "bp", "value": 82, "value2": 128},
                {"kind": "glucose", "value": 5}, {"kind": "spo2", "value": 140},
                {"kind": "weight", "value": 70, "taken_at": (datetime.now(UTC) + timedelta(days=1)).isoformat()}):
        r = client.post(f"/v1/profiles/{pid}/readings", json=bad)
        assert r.status_code == 422, bad
    client.post(f"/v1/profiles/{pid}/readings", json={"kind": "glucose", "value": 132, "context": "fasting",
                                                      "taken_at": "2026-09-01T02:00:00Z"})
    assert len(client.get(f"/v1/profiles/{pid}/readings").json()) == 2
    assert [r["kind"] for r in client.get(f"/v1/profiles/{pid}/readings?kind=glucose").json()] == ["glucose"]

    targets = client.put(f"/v1/profiles/{pid}/reading-targets/bp", json={"high": 130, "high2": 80}).json()
    assert targets == {"bp": {"low": None, "high": "130", "low2": None, "high2": "80"}}
    assert client.put(f"/v1/profiles/{pid}/reading-targets/bp", json={}).json() == {}

    reading = ok.json()["id"]
    as_user("mallory")
    assert client.get(f"/v1/profiles/{pid}/readings").status_code == 404
    assert client.delete(f"/v1/readings/{reading}").status_code == 404
    as_user("alice")
    assert client.delete(f"/v1/readings/{reading}").status_code == 204


def test_emergency_card_prints_what_was_typed_and_is_exported_and_erased(client: TestClient, as_user, sessions) -> None:
    pid = _profile(client)
    empty = client.get(f"/v1/profiles/{pid}/emergency").json()
    assert empty["info"]["contacts"] == [] and empty["out_of_range"] == [] and empty["last_tested"] is None

    info = {"blood_group": "B+", "allergies": " Penicillin ", "conditions": "Type 2 diabetes (told by Dr. Nayak)",
            "medicines": "", "contacts": [{"name": "Priya Mohanty", "phone": "+91 55501 23456", "relation": "wife"}]}
    saved = client.put(f"/v1/profiles/{pid}/emergency", json=info).json()
    assert saved["allergies"] == "Penicillin" and saved["medicines"] is None
    card = client.get(f"/v1/profiles/{pid}/emergency").json()
    assert card["qr_svg"].startswith("data:image/svg+xml")
    text = card["qr_text"].splitlines()
    assert text[0] == "EMERGENCY CARD" and text[1].startswith("Ramesh, ") and "Blood group: B+" in text
    assert "Call: Priya Mohanty (wife) +91 55501 23456" in text and not any(t.startswith("Medicines") for t in text)
    assert client.put(f"/v1/profiles/{pid}/emergency",
                      json={"contacts": [{"name": "A", "phone": "1"}] * 4}).status_code == 422

    client.post(f"/v1/profiles/{pid}/reminders", json={"title": "Eye check", "due_on": "2026-12-01"})
    client.post(f"/v1/profiles/{pid}/readings", json={"kind": "weight", "value": 78.5})
    export = client.get(f"/v1/profiles/{pid}/export").json()
    assert export["emergency_card"]["blood_group"] == "B+" and export["reminders"][0]["title"] == "Eye check"
    assert export["home_readings"]["readings"][0]["value"] == "78.5"

    as_user("mallory")
    assert client.get(f"/v1/profiles/{pid}/emergency").status_code == 404
    as_user("alice")
    assert client.delete(f"/v1/profiles/{pid}").status_code == 204
    with sessions() as s:
        assert s.scalars(select(Reminder)).all() == [] and s.scalars(select(HomeReading)).all() == []


def test_every_email_is_written_in_all_three_languages() -> None:
    for kind, texts in mail.TEXT.items():
        assert set(texts) == {"en", "hi", "or"}, kind
    assert set(reminders.TEXT) == {"en", "hi", "or"}


def test_a_reminder_email_reads_in_the_account_language(client: TestClient, as_user, sessions) -> None:
    pid = _profile(client)
    with sessions.begin() as s:
        s.get(AppUser, as_user("alice").id).preferred_language = "or"
    client.post(f"/v1/profiles/{pid}/reminders", json={"title": "HbA1c", "due_on": "2026-11-19", "note": "ଖାଲି ପେଟ"})
    with sessions.begin() as s:
        assert reminders.send_due(s, today=date(2026, 11, 19)) == 1
    body = mail.outbox[-1].get_content()
    assert mail.outbox[-1]["Subject"] == "ନବ୍ଜ଼ ସ୍ମାରକ: HbA1c"
    assert "ତାରିଖ: 19-11-2026" in body and "ଟିପ୍ପଣୀ: ଖାଲି ପେଟ" in body
