"""REST API: upload → worker → review → confirm, ownership and error format, on a throwaway database."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.api import deps
from app.catalogue import CatalogueData
from app.core.config import settings
from app.core.security import UNUSABLE_PASSWORD_HASH
from app.main import app
from app.models import AppUser, AuditLog, Observation, ProcessingJob
from app.models.enums import JobStage
from app.storage import LocalVolumeStorage
from app.worker.runner import Worker
from app.worker.stages import ExtractionStage

pytestmark = pytest.mark.db
SAMPLES = Path(settings.data_dir) / "synthetic" / "samples"


@pytest.fixture
def storage(tmp_path: Path) -> LocalVolumeStorage:
    return LocalVolumeStorage(tmp_path / "uploads")


@pytest.fixture
def as_user(sessions: sessionmaker[Session]):
    """Returns a function that switches the API's current user; starts as alice."""
    users: dict[str, AppUser] = {}

    def switch(name: str) -> AppUser:
        if name not in users:
            with sessions.begin() as s:
                u = AppUser(email=f"{name}@nabz.local", password_hash=UNUSABLE_PASSWORD_HASH)
                s.add(u)
            users[name] = u
        app.dependency_overrides[deps.current_user] = lambda: users[name]
        return users[name]

    switch("alice")
    return switch


@pytest.fixture
def client(sessions: sessionmaker[Session], storage: LocalVolumeStorage, as_user) -> Iterator[TestClient]:
    app.dependency_overrides[deps.get_sessionmaker] = lambda: sessions
    app.dependency_overrides[deps.get_storage] = lambda: storage
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _profile(client: TestClient, consent: bool = True) -> str:
    r = client.post("/v1/profiles", json={"display_name": "Ramesh", "sex": "male", "date_of_birth": "1968-03-14",
                                          "relationship": "parent", "consent_processing": consent})
    assert r.status_code == 201
    return r.json()["id"]


def _upload(client: TestClient, profile_id: str, sample: str = "syn-2026-0002") -> str:
    with (SAMPLES / f"{sample}.pdf").open("rb") as f:
        r = client.post(f"/v1/profiles/{profile_id}/reports", files={"file": (f"{sample}.pdf", f, "application/pdf")})
    assert r.status_code == 202, r.text
    return r.json()["report_id"]


def _process(sessions: sessionmaker[Session], storage: LocalVolumeStorage, catalogue: CatalogueData) -> None:
    assert Worker(sessions, [ExtractionStage(storage, catalogue)]).run_once()


def test_upload_review_confirm(client: TestClient, sessions, storage, catalogue: CatalogueData) -> None:
    pid = _profile(client)
    rid = _upload(client, pid)
    assert client.get(f"/v1/reports/{rid}").json()["status"] == "queued"
    _process(sessions, storage, catalogue)

    report = client.get(f"/v1/reports/{rid}").json()
    assert report["status"] == "needs_review" and len(report["observations"]) == 53
    assert report["unmapped"] == 0 and report["pages"][0]["source"] == "text-layer"
    wbc = next(o for o in report["observations"] if o["test_code"] == "wbc")
    assert wbc["raw_unit"] == "/cumm" and float(wbc["value"]) < 20  # converted from /cumm to 10^3/µL
    assert client.get(f"/v1/profiles/{pid}/reports").json()[0]["rows"] == 53

    first = report["observations"][0]
    edited = client.patch(f"/v1/observations/{first['id']}", json={"raw_value": "15.6"}).json()
    assert edited["edited"] and edited["test_code"] == first["test_code"] and float(edited["value"]) == 15.6

    added = client.post(f"/v1/reports/{rid}/observations",
                        json={"test_code": "psa", "raw_value": "1.2", "raw_range": "0 - 4"})
    assert added.status_code == 201 and added.json()["unit"] == "ng/mL"
    assert client.delete(f"/v1/observations/{added.json()['id']}").status_code == 204

    confirmed = client.post(f"/v1/reports/{rid}/confirm", json={"collected_at": "2026-03-12"})
    assert confirmed.status_code == 202 and confirmed.json()["status"] == "verified"
    with sessions() as s:
        assert all(o.verified_at for o in s.scalars(select(Observation)))
        assert s.scalars(select(ProcessingJob.stage).order_by(ProcessingJob.id)).all()[-1] == JobStage.ANALYSE
        assert {"report.upload", "observation.edit", "report.confirm"} <= set(s.scalars(select(AuditLog.action)))
    locked = client.patch(f"/v1/observations/{first['id']}", json={"raw_value": "1"})
    assert locked.status_code == 409


def test_confirm_needs_every_row_mapped(client: TestClient, sessions, storage, catalogue: CatalogueData) -> None:
    rid = _upload(client, _profile(client))
    _process(sessions, storage, catalogue)
    row = client.get(f"/v1/reports/{rid}").json()["observations"][0]
    client.patch(f"/v1/observations/{row['id']}", json={"raw_name": "Mystery test"})
    r = client.post(f"/v1/reports/{rid}/confirm", json={})
    assert r.status_code == 409 and r.headers["content-type"] == "application/problem+json"
    assert r.json()["observations"] == [row["id"]]


def test_other_peoples_data_is_invisible(client: TestClient, as_user, sessions, storage,
                                         catalogue: CatalogueData) -> None:
    pid = _profile(client)
    rid = _upload(client, pid)
    as_user("mallory")
    assert client.get(f"/v1/reports/{rid}").status_code == 404
    assert client.get(f"/v1/profiles/{pid}/reports").status_code == 404
    assert client.post(f"/v1/reports/{rid}/confirm", json={}).status_code == 404
    assert client.delete(f"/v1/reports/{rid}").status_code == 404
    assert client.get("/v1/profiles").json() == []


def test_upload_errors_use_problem_details(client: TestClient) -> None:
    no_consent = _profile(client, consent=False)
    r = client.post(f"/v1/profiles/{no_consent}/reports", files={"file": ("a.pdf", b"%PDF-1.4", "application/pdf")})
    assert r.status_code == 400 and "consent" in r.json()["detail"]
    pid = _profile(client)
    r = client.post(f"/v1/profiles/{pid}/reports", files={"file": ("x.gif", b"GIF89a", "image/gif")})
    assert r.status_code == 400 and r.json()["title"] == "Bad request"
    rid = _upload(client, pid)
    dup = client.post(f"/v1/profiles/{pid}/reports",
                      files={"file": ("a.pdf", (SAMPLES / "syn-2026-0002.pdf").read_bytes(), "application/pdf")})
    assert dup.status_code == 409 and dup.json()["report_id"] == rid


def test_events_page_image_and_delete(client: TestClient, sessions, storage, catalogue: CatalogueData) -> None:
    rid = _upload(client, _profile(client), "syn-2026-0003")
    _process(sessions, storage, catalogue)
    events = client.get(f"/v1/reports/{rid}/events")
    assert events.headers["content-type"].startswith("text/event-stream")
    assert 'data: {"status": "needs_review"}' in events.text
    image = client.get(f"/v1/reports/{rid}/pages/0/image")
    assert image.status_code == 200 and image.content.startswith(b"\x89PNG")
    assert client.get(f"/v1/reports/{rid}/pages/9/image").status_code == 404
    assert client.delete(f"/v1/reports/{rid}").status_code == 204
    assert client.get(f"/v1/reports/{rid}").status_code == 404
    assert not any(storage.root.rglob("*.pdf"))


def test_catalogue_is_public(client: TestClient) -> None:
    tests = client.get("/v1/catalogue/tests").json()
    assert len(tests) == 70 and {"code": "hba1c", "organ": "pancreas"}.items() <= next(
        t for t in tests if t["code"] == "hba1c").items()


def test_sign_in_is_required_without_dev_auth(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    app.dependency_overrides.pop(deps.current_user)
    monkeypatch.setattr(settings, "dev_auth", False)
    r = client.get("/v1/profiles")
    assert r.status_code == 401 and r.json()["title"] == "Not signed in"
