"""REST API: upload → worker → review → confirm, ownership and error format, on a throwaway database."""

from collections.abc import Iterator
from datetime import UTC, datetime
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
from app.worker.stages import AnalysisStage, ExplanationStage, ExtractionStage

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
                u = AppUser(email=f"{name}@nabz.local", password_hash=UNUSABLE_PASSWORD_HASH,
                            email_verified_at=datetime.now(UTC))
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


def test_a_sample_report_goes_through_the_same_steps(client: TestClient, sessions, storage,
                                                      catalogue: CatalogueData) -> None:
    pid = _profile(client)
    r = client.post(f"/v1/profiles/{pid}/sample-report")
    assert r.status_code == 202, r.text
    rid = r.json()["report_id"]
    _process(sessions, storage, catalogue)
    report = client.get(f"/v1/reports/{rid}").json()
    assert report["status"] == "needs_review" and len(report["observations"]) >= 40
    assert report["lab_name"] == "Anvaya Diagnostics"
    listed = client.get(f"/v1/profiles/{pid}/reports").json()
    assert listed[0]["note"].startswith("Sample report from the walkthrough")
    # trying it twice opens the first one
    again = client.post(f"/v1/profiles/{pid}/sample-report")
    assert again.status_code == 409 and again.json()["report_id"] == rid


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
    original = client.get(f"/v1/reports/{rid}/file")
    assert original.headers["content-type"] == "application/pdf" and original.content.startswith(b"%PDF-")
    assert client.delete(f"/v1/reports/{rid}").status_code == 204
    assert client.get(f"/v1/reports/{rid}").status_code == 404
    assert not any(storage.root.rglob("*.pdf"))


def test_catalogue_is_public(client: TestClient) -> None:
    tests = client.get("/v1/catalogue/tests").json()
    assert len(tests) == 70 and {"code": "hba1c", "organ": "pancreas"}.items() <= next(
        t for t in tests if t["code"] == "hba1c").items()


def test_sign_in_is_required(client: TestClient) -> None:
    app.dependency_overrides.pop(deps.current_user)
    r = client.get("/v1/profiles")
    assert r.status_code == 401 and r.json()["title"] == "Not signed in"


def _read_and_confirm(client: TestClient, sessions, storage, catalogue: CatalogueData, pid: str, sample: str) -> str:
    rid = _upload(client, pid, sample)
    _process(sessions, storage, catalogue)
    assert client.post(f"/v1/reports/{rid}/confirm", json={}).status_code == 202
    assert Worker(sessions, [AnalysisStage()]).run_once()
    return rid


def test_insights_history_and_watch_list(client: TestClient, sessions, storage, catalogue: CatalogueData) -> None:
    pid = _profile(client)
    rids = [_read_and_confirm(client, sessions, storage, catalogue, pid, f"hist-2026-00-v{k}") for k in range(3)]

    insights = client.get(f"/v1/reports/{rids[2]}/insights").json()
    assert insights["analysed"] and insights["report"]["status"] == "explaining"
    assert insights["report"]["collected_at"] == "2026-07-04"  # read from the report header
    assert insights["person"]["display_name"] == "Ramesh" and insights["person"]["age"] == 58
    severities = [o["status"] for o in insights["organs"]]
    assert severities[0] != "normal" or set(severities) <= {"normal", "unknown"}  # worst organ first
    creat = next(r for o in insights["organs"] for r in o["results"] if r["test_code"] == "creatinine")
    assert creat["previous"]["date"] == "2025-06-04" and creat["change"]["rcv_up"] > 0
    assert creat["trend"]["n"] == 3 and creat["trend"]["reason"] in ("too_few", "short_span")
    assert creat["percentile"]["population"].startswith("US population")

    history = client.get(f"/v1/profiles/{pid}/tests/creatinine").json()
    assert [r["date"] for r in history["results"]] == ["2024-07-02", "2025-06-04", "2026-07-04"]
    assert history["test"]["unit"] == "mg/dL" and history["test"]["rcv_up"] > 0
    assert client.get(f"/v1/profiles/{pid}/tests/no_such_test").status_code == 404
    for w in client.get(f"/v1/profiles/{pid}/watch").json():
        assert w["confirmed"] or w["rcv_significant"]

    frames = client.get(f"/v1/profiles/{pid}/body-map").json()
    assert [f["date"] for f in frames] == ["2024-07-02", "2025-06-04", "2026-07-04"]
    assert [f["report_id"] for f in frames] == rids
    kidney = next(o for o in frames[2]["organs"] if o["code"] == "kidney")
    assert kidney["results"] >= 1 and kidney["status"] == next(
        o["status"] for o in insights["organs"] if o["code"] == "kidney")
    assert frames[2]["organs"][0]["out_of_range"] > 0 or all(o["out_of_range"] == 0 for o in frames[2]["organs"])

    # Deleting the middle report makes the first one the latest report's "previous" result.
    assert client.delete(f"/v1/reports/{rids[1]}").status_code == 204
    creat = next(r for o in client.get(f"/v1/reports/{rids[2]}/insights").json()["organs"]
                 for r in o["results"] if r["test_code"] == "creatinine")
    assert creat["previous"]["date"] == "2024-07-02" and creat["trend"] is None


def test_insights_are_private(client: TestClient, as_user, sessions, storage, catalogue: CatalogueData) -> None:
    pid = _profile(client)
    rid = _upload(client, pid)
    as_user("mallory")
    assert client.get(f"/v1/reports/{rid}/insights").status_code == 404
    assert client.get(f"/v1/reports/{rid}/file").status_code == 404
    assert client.get(f"/v1/profiles/{pid}/tests/hb").status_code == 404
    assert client.get(f"/v1/profiles/{pid}/watch").status_code == 404
    assert client.get(f"/v1/profiles/{pid}/body-map").status_code == 404


class FakeTTS:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def synthesize(self, text: str, language: str) -> bytes:
        self.calls.append((text, language))
        return b"ID3fake-mp3"


def test_consents_explanations_narration_and_feedback(client: TestClient, sessions, storage,
                                                      catalogue: CatalogueData) -> None:
    from app.api.routes import explanations

    pid = _profile(client)
    consents = {c["purpose"]: c["granted"] for c in client.get(f"/v1/profiles/{pid}/consents").json()}
    assert consents == {"processing": True, "external_ai": False, "voice": False, "research": False}
    assert client.put(f"/v1/profiles/{pid}/consents/processing", json={"granted": False}).status_code == 409

    rid = _read_and_confirm(client, sessions, storage, catalogue, pid, "syn-2026-0002")
    assert client.get(f"/v1/reports/{rid}/explanation?lang=en").json()["state"] == "pending"  # queued by analysis
    assert Worker(sessions, [ExplanationStage(None, None)]).run_once()
    state = client.get(f"/v1/reports/{rid}/explanation?lang=en").json()
    assert state["state"] == "ready" and client.get(f"/v1/reports/{rid}").json()["status"] == "explained"
    ex = state["explanation"]
    assert ex["source"] == "template" and ex["reason"] == "no_consent" and ex["disclaimer_key"] == "not_a_diagnosis_v1"

    # Another language is written on request.
    assert client.post(f"/v1/reports/{rid}/explanation", json={"language": "hi"}).json()["state"] == "pending"
    assert Worker(sessions, [ExplanationStage(None, None)]).run_once()
    hi = client.get(f"/v1/reports/{rid}/explanation?lang=hi").json()["explanation"]
    assert hi["language"] == "hi" and "सीमा" in hi["summary"]

    # Narration needs voice consent; then it's generated once and reused.
    tts = FakeTTS()
    app.dependency_overrides[explanations.get_tts] = lambda: tts
    r = client.post(f"/v1/explanations/{ex['id']}/audio")
    assert r.status_code == 409 and r.json()["consent"] == "voice"
    assert client.put(f"/v1/profiles/{pid}/consents/voice", json={"granted": True}).json()["granted"] is True
    url = client.post(f"/v1/explanations/{ex['id']}/audio").json()["url"]
    client.post(f"/v1/explanations/{ex['id']}/audio")
    audio = client.get(url)
    assert audio.headers["content-type"] == "audio/mpeg" and audio.content == b"ID3fake-mp3" and len(tts.calls) == 1
    assert tts.calls[0][0].startswith("Your results.")

    assert client.post(f"/v1/explanations/{ex['id']}/feedback", json={"helpful": True}).status_code == 201
    assert client.put(f"/v1/profiles/{pid}/consents/voice", json={"granted": False}).json()["granted"] is False
    with sessions() as s:
        assert {"consent.set", "explanation.request", "explanation.narrate"} <= set(s.scalars(select(AuditLog.action)))


def test_explanations_are_private(client: TestClient, as_user, sessions, storage, catalogue: CatalogueData) -> None:
    pid = _profile(client)
    rid = _read_and_confirm(client, sessions, storage, catalogue, pid, "syn-2026-0002")
    Worker(sessions, [ExplanationStage(None, None)]).run_once()
    eid = client.get(f"/v1/reports/{rid}/explanation?lang=en").json()["explanation"]["id"]
    as_user("mallory")
    assert client.get(f"/v1/reports/{rid}/explanation").status_code == 404
    assert client.post(f"/v1/explanations/{eid}/audio").status_code == 404
    assert client.get(f"/v1/profiles/{pid}/consents").status_code == 404


def test_export_and_delete_a_person(client: TestClient, as_user, sessions, storage, catalogue: CatalogueData) -> None:
    from app.api.routes import explanations

    pid = _profile(client)
    rid = _read_and_confirm(client, sessions, storage, catalogue, pid, "syn-2026-0002")
    Worker(sessions, [ExplanationStage(None, None)]).run_once()
    eid = client.get(f"/v1/reports/{rid}/explanation?lang=en").json()["explanation"]["id"]
    app.dependency_overrides[explanations.get_tts] = FakeTTS
    client.put(f"/v1/profiles/{pid}/consents/voice", json={"granted": True})
    client.post(f"/v1/explanations/{eid}/audio")
    assert {p.suffix for p in storage.root.rglob("*") if p.is_file()} == {".pdf", ".mp3"}

    r = client.get(f"/v1/profiles/{pid}/export")
    assert r.status_code == 200 and r.headers["content-disposition"].startswith('attachment; filename="nabz-ramesh-')
    data = r.json()
    assert data["format"] == "nabz-export" and data["person"]["display_name"] == "Ramesh"
    assert {c["purpose"] for c in data["consents"]} == {"processing", "voice"}
    report = data["reports"][0]
    hb = next(x for x in report["results"] if x["test_code"] == "hb")
    assert hb["organ_system"] == "blood" and hb["as_printed"]["value"] and hb["confirmed_at"]
    assert report["explanations"][0]["content"]["summary"] and report["files"][0]["sha256"]

    as_user("mallory")
    assert client.get(f"/v1/profiles/{pid}/export").status_code == 404
    assert client.delete(f"/v1/profiles/{pid}").status_code == 404
    as_user("alice")
    assert client.delete(f"/v1/profiles/{pid}").status_code == 204
    assert client.get(f"/v1/reports/{rid}").status_code == 404 and client.get("/v1/profiles").json() == []
    assert not any(p.is_file() for p in storage.root.rglob("*"))  # the upload and the narration audio
    with sessions() as s:
        assert s.scalars(select(Observation)).all() == []
        entry = s.scalars(select(AuditLog).where(AuditLog.action == "profile.delete")).one()
        assert entry.meta == {"files": 2}


def test_other_records_are_private_exported_and_erased(client: TestClient, as_user, sessions, storage) -> None:
    pid = _profile(client)
    jpeg = b"\xff\xd8\xff\xe0" + b"0" * 2000
    r = client.post(f"/v1/profiles/{pid}/records", data={"kind": "imaging", "title": "X-ray left knee",
                                                          "record_date": "2025-04-12", "facility": "Utkal Imaging"},
                    files={"file": ("knee.jpg", jpeg, "image/jpeg")})
    assert r.status_code == 201, r.text
    rec = r.json()
    assert rec["mime_type"] == "image/jpeg" and rec["record_date"] == "2025-04-12"
    assert client.post(f"/v1/profiles/{pid}/records", data={"kind": "other", "title": "x"},
                       files={"file": ("a.txt", b"hello", "text/plain")}).status_code == 400
    assert client.get(f"/v1/records/{rec['id']}/file").content == jpeg
    assert client.patch(f"/v1/records/{rec['id']}", json={"title": ""}).status_code == 422
    edited = client.patch(f"/v1/records/{rec['id']}", json={"notes": "  pain climbing stairs "}).json()
    assert edited["notes"] == "pain climbing stairs" and edited["title"] == "X-ray left knee"
    assert [x["title"] for x in client.get(f"/v1/profiles/{pid}/records").json()] == ["X-ray left knee"]
    assert client.get(f"/v1/profiles/{pid}/export").json()["other_records"][0]["facility"] == "Utkal Imaging"

    as_user("mallory")
    assert client.get(f"/v1/records/{rec['id']}/file").status_code == 404
    assert client.delete(f"/v1/records/{rec['id']}").status_code == 404
    as_user("alice")
    assert client.delete(f"/v1/profiles/{pid}").status_code == 204
    assert not any(p.is_file() for p in storage.root.rglob("*"))


def test_exact_values_everywhere(client: TestClient, sessions, storage, catalogue: CatalogueData) -> None:
    pid = _profile(client)
    rids = [_read_and_confirm(client, sessions, storage, catalogue, pid, f"hist-2026-00-v{k}") for k in range(2)]

    reports = {r["id"]: r for r in client.get(f"/v1/profiles/{pid}/reports").json()}
    flagged = reports[rids[1]]["out_of_range"]
    assert flagged and all(f["status"] not in ("normal", "unknown") for f in flagged)
    assert {"test_name", "value", "unit", "ref_low", "ref_high", "date"} <= flagged[0].keys()

    note = client.patch(f"/v1/reports/{rids[1]}", json={"note": " Not fasting "}).json()
    assert note["note"] == "Not fasting"
    listed = client.get(f"/v1/profiles/{pid}/reports").json()
    assert next(r for r in listed if r["id"] == rids[1])["note"] == "Not fasting"

    person = client.get("/v1/profiles").json()[0]
    assert person["last_tested"] == "2025-06-04"
    assert {a["test_code"] for a in person["attention"]} == {f["test_code"] for f in flagged}

    frame = client.get(f"/v1/profiles/{pid}/body-map").json()[-1]
    kidney = next(o for o in frame["organs"] if o["code"] == "kidney")
    assert len(kidney["tests"]) == kidney["results"] and kidney["tests"][0]["value"]

    organ = client.get(f"/v1/profiles/{pid}/organs/kidney").json()
    creat = next(t for t in organ["tests"] if t["test"]["code"] == "creatinine")
    assert organ["names"]["en"] == "Kidneys" and [r["date"] for r in creat["results"]] == ["2024-07-02", "2025-06-04"]
    assert client.get(f"/v1/profiles/{pid}/organs/spleen").status_code == 404


def test_imaging_record_keeps_its_study_image_and_report_text(client: TestClient, storage, tmp_path: Path) -> None:
    from datetime import date

    from tools.family.story import CREDITS, FAMILY, IMAGING_CENTRES
    from tools.synthetic.imaging import ImagingCentre, ImagingSpec, render_imaging_pdf

    study = FAMILY[4].imaging[0]  # knee MRI
    pdf = tmp_path / "mri.pdf"
    render_imaging_pdf(ImagingSpec(ImagingCentre(study.centre, **IMAGING_CENTRES[study.centre]), "Test Person", 26,
                                   "male", "Dr. Test", date(2023, 11, 9), "RAD0001", study.title, study.history,
                                   study.technique, study.findings, study.impression,
                                   Path(settings.data_dir) / "imaging" / study.image, CREDITS[study.image]), pdf)
    pid = _profile(client)
    rec = client.post(f"/v1/profiles/{pid}/records", data={"kind": "imaging", "title": "MRI right knee"},
                      files={"file": ("mri.pdf", pdf.read_bytes(), "application/pdf")}).json()
    assert rec["has_image"] and rec["study_title"] == "MRI RIGHT KNEE"
    assert rec["findings"][1] == "Cruciate and collateral ligaments are intact."
    assert rec["impression"] == study.impression and rec["image_credit"].startswith("Image: Pil Kang")
    image = client.get(f"/v1/records/{rec['id']}/image")
    assert image.headers["content-type"] == "image/jpeg" and image.content.startswith(b"\xff\xd8")

    plain = client.post(f"/v1/profiles/{pid}/records", data={"kind": "prescription", "title": "Rx"},
                        files={"file": ("rx.pdf", pdf.read_bytes(), "application/pdf")}).json()
    assert not plain["has_image"] and client.get(f"/v1/records/{plain['id']}/image").status_code == 404

    assert client.delete(f"/v1/records/{rec['id']}").status_code == 204
    assert client.delete(f"/v1/records/{plain['id']}").status_code == 204
    assert not any(p.is_file() for p in storage.root.rglob("*"))


def test_sharing_a_report_with_a_doctor(client: TestClient, as_user, sessions, storage,
                                        catalogue: CatalogueData) -> None:
    from datetime import timedelta

    from app.api.routes import shares
    from app.models import ShareLink

    shares.view_limiter.reset()
    pid = _profile(client)
    rid = _read_and_confirm(client, sessions, storage, catalogue, pid, "syn-2026-0002")
    Worker(sessions, [ExplanationStage(None, None)]).run_once()
    client.patch(f"/v1/reports/{rid}", json={"note": "Not fasting"})

    made = client.post(f"/v1/reports/{rid}/shares", json={"days": 7, "label": "Dr. Nayak"})
    assert made.status_code == 201
    link = made.json()
    token = link["url"].rsplit("/s/", 1)[1]
    assert link["active"] and link["qr_svg"].startswith("data:image/svg+xml") and link["label"] == "Dr. Nayak"
    with sessions() as s:  # only the hash is kept
        stored = s.scalars(select(ShareLink)).one()
        assert stored.token_hash != token and len(stored.token_hash) == 64

    # no session is needed, and nothing but this report is shown
    app.dependency_overrides.pop(deps.current_user)
    shared = client.get(f"/v1/shared/{token}")
    assert shared.status_code == 200
    body = shared.json()
    assert body["person"] == {"display_name": "Ramesh", "sex": "male", "age": body["person"]["age"]}
    assert body["note"] == "Not fasting" and body["organs"] and len(body["questions"]) >= 2
    assert "id" not in body["person"]
    assert client.get("/v1/shared/not-a-token").status_code == 404
    assert client.get("/v1/profiles").status_code == 401

    as_user("mallory")
    assert client.post(f"/v1/reports/{rid}/shares", json={"days": 7}).status_code == 404
    assert client.delete(f"/v1/shares/{link['id']}").status_code == 404
    as_user("alice")
    listed = client.get(f"/v1/reports/{rid}/shares").json()
    assert listed[0]["views"] == 1 and listed[0]["last_viewed_at"]

    # an expired link and a withdrawn link both stop working, with the same answer
    with sessions.begin() as s:
        s.scalars(select(ShareLink)).one().expires_at -= timedelta(days=8)
    assert client.get(f"/v1/shared/{token}").status_code == 404
    second = client.post(f"/v1/reports/{rid}/shares", json={"days": 1}).json()
    token2 = second["url"].rsplit("/s/", 1)[1]
    assert client.get(f"/v1/shared/{token2}").status_code == 200
    assert client.delete(f"/v1/shares/{second['id']}").status_code == 204
    gone = client.get(f"/v1/shared/{token2}")
    assert gone.status_code == 404 and "expired or was withdrawn" in gone.json()["detail"]
    with sessions() as s:
        assert {"share.create", "share.view", "share.revoke"} <= set(s.scalars(select(AuditLog.action)))
