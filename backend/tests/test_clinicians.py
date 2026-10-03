"""Doctors on Nabz: registration and verification, sharing a report with a verified doctor, the doctor's read-only
view and notes, withdrawal, and who may see what."""

from collections.abc import Iterator
from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.api import deps
from app.core.security import UNUSABLE_PASSWORD_HASH
from app.main import app
from app.models import AppUser, AuditLog, Profile, Report
from app.models.enums import ReportStatus, Sex, UserRole
from app.services.analysis import analyse_profile
from tests.factories import add_report

pytestmark = pytest.mark.db


@pytest.fixture
def people(sessions: sessionmaker[Session]) -> dict[str, AppUser]:
    made = {}
    with sessions.begin() as s:
        for name, role in (("family", UserRole.USER), ("doctor", UserRole.CLINICIAN), ("other", UserRole.CLINICIAN),
                           ("admin", UserRole.ADMIN)):
            u = AppUser(email=f"{name}@nabz.local", password_hash=UNUSABLE_PASSWORD_HASH, role=role,
                        email_verified_at=datetime.now(UTC),
                        totp_enabled_at=datetime.now(UTC) if role is UserRole.ADMIN else None)
            s.add(u)
            made[name] = u
    return made


@pytest.fixture
def client(sessions: sessionmaker[Session], people) -> Iterator[TestClient]:
    app.dependency_overrides[deps.get_sessionmaker] = lambda: sessions
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def as_(who: AppUser) -> None:
    app.dependency_overrides[deps.current_user] = lambda: who


@pytest.fixture
def report(sessions: sessionmaker[Session], people) -> str:
    with sessions.begin() as s:
        p = Profile(owner_user_id=people["family"].id, display_name="Ramesh Mohanty", sex=Sex.MALE,
                    date_of_birth=date(1968, 3, 14))
        s.add(p)
        s.flush()
        r = add_report(s, p.id, people["family"].id, date(2026, 8, 19), {"hba1c": (7.6, 4.0, 5.6)})
        r.status, r.lab_name, r.note = ReportStatus.EXPLAINED, "Anvaya Diagnostics", "Fasting sample"
        analyse_profile(s, p.id)
        return str(r.id)


REGISTRATION = {"full_name": "Dr. Prakash Nayak", "registration_no": "OCMR 12345",
                "council": "Odisha Council of Medical Registration", "specialty": "General medicine"}


def test_a_verified_doctor_reads_a_shared_report_and_leaves_a_note(client: TestClient, people, report,
                                                                   sessions) -> None:
    # the doctor registers; until an admin verifies it, nothing can be shared with them
    as_(people["doctor"])
    assert client.get("/v1/clinician/me").json() is None
    assert client.put("/v1/clinician/me", json=REGISTRATION).json()["verified_at"] is None
    as_(people["family"])
    refused = client.post(f"/v1/reports/{report}/grants", json={"email": "doctor@nabz.local"})
    assert refused.status_code == 404 and refused.json()["code"] == "no_clinician"
    # a member's email gets the same answer, so the endpoint doesn't reveal who has an account
    assert client.post(f"/v1/reports/{report}/grants", json={"email": "admin@nabz.local"}).json()["code"] == \
        "no_clinician"

    as_(people["admin"])
    listed = client.get("/v1/admin/clinicians").json()
    assert [(c["email"], c["verified_at"]) for c in listed] == [("doctor@nabz.local", None)]
    assert client.post(f"/v1/admin/clinicians/{people['doctor'].id}/verify", json={"verified": True}).json()[
        "verified_at"]

    as_(people["family"])
    grant = client.post(f"/v1/reports/{report}/grants", json={"email": " Doctor@nabz.local "}).json()
    assert grant["clinician_name"] == "Dr. Prakash Nayak" and grant["registration_no"] == "OCMR 12345"
    again = client.post(f"/v1/reports/{report}/grants", json={"email": "doctor@nabz.local"}).json()
    assert again["id"] == grant["id"]  # sharing twice keeps one share

    as_(people["doctor"])
    shared = client.get("/v1/clinician/shared").json()
    assert [(s["person"]["display_name"], s["lab_name"]) for s in shared] == [("Ramesh Mohanty", "Anvaya Diagnostics")]
    view = client.get(f"/v1/clinician/reports/{report}").json()
    assert view["note"] == "Fasting sample" and view["organs"][0]["results"][0]["test_code"] == "hba1c"
    note = client.post(f"/v1/clinician/reports/{report}/notes", json={"text": "Repeat HbA1c in three months."})
    assert note.status_code == 201 and note.json()["clinician_name"] == "Dr. Prakash Nayak"

    as_(people["other"])  # another clinician, even a verified one, sees nothing that wasn't shared with them
    client.put("/v1/clinician/me", json={**REGISTRATION, "full_name": "Dr. Other", "registration_no": "OCMR 2"})
    assert client.get(f"/v1/clinician/reports/{report}").status_code == 404
    assert client.get("/v1/clinician/shared").json() == []

    as_(people["family"])
    assert [n["text"] for n in client.get(f"/v1/reports/{report}/notes").json()] == ["Repeat HbA1c in three months."]
    assert client.get(f"/v1/reports/{report}/grants").json()[0]["notes"] == 1
    profile_id = client.get("/v1/profiles").json()[0]["id"]
    export = client.get(f"/v1/profiles/{profile_id}/export").json()
    assert export["reports"][0]["doctors_notes"][0]["doctor"] == "Dr. Prakash Nayak"
    assert client.delete(f"/v1/grants/{grant['id']}").status_code == 204

    as_(people["doctor"])  # withdrawn: gone from the list, and the report can't be opened
    assert client.get("/v1/clinician/shared").json() == []
    assert client.get(f"/v1/clinician/reports/{report}").status_code == 404
    with sessions() as s:
        actions = [a for a in s.scalars(select(AuditLog.action).where(AuditLog.action.like("clinician.%")))]
        assert actions.count("clinician.view") == 1 and "clinician.note" in actions


def test_a_changed_registration_must_be_verified_again_and_roles_are_kept_apart(client: TestClient, people,
                                                                                report) -> None:
    as_(people["doctor"])
    client.put("/v1/clinician/me", json=REGISTRATION)
    as_(people["admin"])
    client.post(f"/v1/admin/clinicians/{people['doctor'].id}/verify", json={"verified": True})
    as_(people["doctor"])
    assert client.put("/v1/clinician/me", json={**REGISTRATION, "specialty": "Diabetology"}).json()["verified_at"]
    assert client.put("/v1/clinician/me", json={**REGISTRATION, "registration_no": "OCMR 99"}).json()[
        "verified_at"] is None
    # a family member isn't a clinician, and a clinician can't verify anyone
    as_(people["family"])
    assert client.get("/v1/clinician/shared").status_code == 403
    as_(people["doctor"])
    assert client.post(f"/v1/admin/clinicians/{people['doctor'].id}/verify", json={"verified": True}).status_code == 403


def test_deleting_the_report_ends_the_share(client: TestClient, people, report, sessions) -> None:
    as_(people["doctor"])
    client.put("/v1/clinician/me", json=REGISTRATION)
    as_(people["admin"])
    client.post(f"/v1/admin/clinicians/{people['doctor'].id}/verify", json={"verified": True})
    as_(people["family"])
    client.post(f"/v1/reports/{report}/grants", json={"email": "doctor@nabz.local"})
    assert client.delete(f"/v1/reports/{report}").status_code == 204
    as_(people["doctor"])
    assert client.get("/v1/clinician/shared").json() == []
    with sessions() as s:
        assert s.get(Report, report) is None
