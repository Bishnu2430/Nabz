"""People in a family: consent for children (FR-05) and correcting a person's details (FR-02)."""

from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.api import deps
from app.core.security import UNUSABLE_PASSWORD_HASH
from app.main import app
from app.models import AppUser, Explanation, Observation, ProcessingJob, Report
from app.models.enums import JobStage, ObsStatus, ReportStatus, SafetyStatus
from app.services.analysis import analyse_profile
from app.services.interpretation import lab_test_ids
from app.storage import LocalVolumeStorage

pytestmark = pytest.mark.db


@pytest.fixture
def client(sessions: sessionmaker[Session], tmp_path: Path) -> Iterator[TestClient]:
    with sessions.begin() as s:
        user = AppUser(email="asha@nabz.local", password_hash=UNUSABLE_PASSWORD_HASH,
                       email_verified_at=datetime.now(UTC))
        s.add(user)
    app.dependency_overrides[deps.get_sessionmaker] = lambda: sessions
    app.dependency_overrides[deps.get_storage] = lambda: LocalVolumeStorage(tmp_path / "uploads")
    app.dependency_overrides[deps.current_user] = lambda: user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def years_ago(n: int) -> str:
    today = date.today()
    return date(today.year - n, today.month, min(today.day, 28)).isoformat()


def person(**over) -> dict:
    return {"display_name": "Ananya", "sex": "female", "date_of_birth": years_ago(12), "relationship": "child",
            "consent_processing": True, **over}


def test_a_child_needs_a_parent_or_guardian_to_consent(client: TestClient) -> None:
    refused = client.post("/v1/profiles", json=person())
    assert refused.status_code == 422 and refused.json()["code"] == "guardian_required"
    made = client.post("/v1/profiles", json=person(guardian_confirmed=True))
    assert made.status_code == 201 and made.json()["guardian_confirmed_at"]
    # an adult needs no such confirmation, and someone under 18 can't be the account holder
    assert client.post("/v1/profiles", json=person(date_of_birth=years_ago(30))).json()["guardian_confirmed_at"] is None
    assert client.post("/v1/profiles", json=person(relationship="self", guardian_confirmed=True)).json()["code"] == \
        "self_minor"
    export = client.get(f"/v1/profiles/{made.json()['id']}/export").json()
    assert export["person"]["guardian_confirmed_at"]


def test_correcting_a_birth_date_to_a_child_asks_for_the_guardian_too(client: TestClient) -> None:
    pid = client.post("/v1/profiles", json=person(date_of_birth=None)).json()["id"]
    assert client.patch(f"/v1/profiles/{pid}", json={"date_of_birth": years_ago(10)}).json()["code"] == \
        "guardian_required"
    done = client.patch(f"/v1/profiles/{pid}", json={"date_of_birth": years_ago(10), "guardian_confirmed": True})
    assert done.status_code == 200 and done.json()["date_of_birth"] == years_ago(10)
    assert client.put(f"/v1/profiles/{pid}/consents/voice", json={"granted": True}).json()["granted"] is True


def test_changing_sex_rereads_typical_ranges_and_rewrites_what_changed(client: TestClient, sessions) -> None:
    pid = client.post("/v1/profiles", json=person(display_name="Priya", date_of_birth="1974-06-18",
                                                  relationship="self")).json()["id"]
    with sessions.begin() as s:
        user_id = s.scalar(select(AppUser.id))
        report = Report(profile_id=pid, uploaded_by=user_id, collected_at=date(2026, 5, 1),
                        status=ReportStatus.EXPLAINED, source_sha256="x" * 64)
        s.add(report)
        s.flush()
        # no printed range: the typical range for a woman (12.0–15.0) makes 12.5 g/dL normal
        s.add(Observation(report_id=report.id, test_id=lab_test_ids(s)["hb"], raw_name="Haemoglobin", raw_value="12.5",
                          raw_unit="g/dL", value_num=Decimal("12.5"), unit="g/dL", ref_low=Decimal("12.0"),
                          ref_high=Decimal("15.0"), ref_source="catalogue", confidence=1.0,
                          verified_at=datetime.now(UTC)))
        s.add(Explanation(report_id=report.id, language="en", model_id="template", prompt_version="explain-v5",
                          safety_status=SafetyStatus.FALLBACK, content={"summary": "All results are within range."}))
        s.flush()
        analyse_profile(s, report.profile_id)
        report_id = report.id
    with sessions() as s:
        assert s.scalar(select(Observation.status)) is ObsStatus.NORMAL

    edited = client.patch(f"/v1/profiles/{pid}", json={"sex": "male", "display_name": "Prakash"})
    assert edited.status_code == 200 and edited.json()["display_name"] == "Prakash"
    with sessions() as s:
        obs = s.scalar(select(Observation))
        assert (obs.ref_low, obs.ref_high, obs.status) == (Decimal("13.0"), Decimal("17.0"), ObsStatus.LOW)
        # the old explanation said "within range": it goes, and a new one is queued in the same language
        assert s.scalars(select(Explanation)).all() == []
        job = s.scalar(select(ProcessingJob).where(ProcessingJob.report_id == report_id))
        assert job.stage is JobStage.EXPLAIN and job.args == {"lang": "en"}
