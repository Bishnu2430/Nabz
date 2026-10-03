"""The catalogue and the knowledge base on the console (FR-35, FR-36): edits are validated, audited and used by the
interpreter at once; a critical limit applies only after clinical review; knowledge documents are chunked, embedded,
re-embedded and deleted."""

from collections.abc import Iterator
from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.api import deps
from app.api.routes.ask import get_embedder
from app.catalogue.seed import seed_catalogue
from app.core.security import UNUSABLE_PASSWORD_HASH
from app.extraction.interpret import RawRow
from app.knowledge.embed import HashEmbedder
from app.main import app
from app.models import AppUser, AuditLog, KbDocument, Observation, ProcessingJob, Profile
from app.models.enums import JobStage, ObsStatus, ReportStatus, Sex, UserRole
from app.services.analysis import analyse_profile
from app.services.catalogue_admin import chunk_text
from app.services.interpretation import current_interpreter
from tests.factories import add_report

pytestmark = pytest.mark.db
KB_URL = "https://medlineplus.gov/lab-tests/hemoglobin-a1c-hba1c-test/"


@pytest.fixture
def staff(sessions: sessionmaker[Session], catalogue) -> Iterator[dict[str, AppUser]]:
    made = {}
    with sessions.begin() as s:
        for name, role in (("admin", UserRole.ADMIN), ("reviewer", UserRole.REVIEWER), ("family", UserRole.USER)):
            u = AppUser(email=f"{name}@nabz.local", password_hash=UNUSABLE_PASSWORD_HASH, role=role,
                        email_verified_at=datetime.now(UTC), totp_enabled_at=datetime.now(UTC))
            s.add(u)
            made[name] = u
    yield made
    # the catalogue is shared by every test: put it back as shipped, and drop the documents added here
    with sessions.begin() as s:
        seed_catalogue(s, catalogue)
        s.execute(delete(KbDocument).where(KbDocument.url.like("https://medlineplus.gov/lab-tests/%")))


@pytest.fixture
def client(sessions: sessionmaker[Session], staff) -> Iterator[TestClient]:
    app.dependency_overrides[deps.get_sessionmaker] = lambda: sessions
    app.dependency_overrides[get_embedder] = HashEmbedder
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def as_(who: AppUser) -> None:
    app.dependency_overrides[deps.current_user] = lambda: who


def test_an_alias_is_used_at_once_and_a_clash_is_refused(client: TestClient, staff, sessions) -> None:
    raw = RawRow("Glyco Hb", "7.6", "%", None, None, None, 1.0, "manual")
    with sessions() as s:
        assert current_interpreter(s).interpret(raw, "male", 58).test_code != "hba1c"

    as_(staff["admin"])
    test = client.get("/v1/admin/catalogue/hba1c").json()
    edited = client.patch("/v1/admin/catalogue/hba1c", json={"aliases": [*test["aliases"], "Glyco  Hb", "glyco-hb"]})
    assert edited.status_code == 200
    assert edited.json()["aliases"][-1] == "Glyco Hb"  # spaces tidied, and the same name twice kept once
    assert edited.json()["history"][0]["meta"]["after"]["aliases"][-1] == "Glyco Hb"
    with sessions() as s:
        assert current_interpreter(s).interpret(raw, "male", 58).test_code == "hba1c"

    clash = client.patch("/v1/admin/catalogue/hba1c", json={"aliases": ["S. Creatinine"]})
    assert clash.status_code == 409 and clash.json()["code"] == "alias_taken" and clash.json()["test"] == "creatinine"
    order = client.patch("/v1/admin/catalogue/hba1c", json={"plausible_min": 30, "plausible_max": 3})
    assert order.json()["code"] == "plausible_order"
    listed = client.get("/v1/admin/catalogue", params={"q": "glyco"}).json()
    assert [t["code"] for t in listed] == ["hba1c"]


def test_ranges_and_units_are_checked_before_they_are_saved(client: TestClient, staff, sessions) -> None:
    as_(staff["admin"])
    bad = client.put("/v1/admin/catalogue/hba1c/ranges", json=[{"low": 6, "high": 5}])
    assert bad.status_code == 422 and bad.json()["code"] == "range_invalid"
    own = client.put("/v1/admin/catalogue/hba1c/conversions", json=[{"from_unit": "%", "factor": 1}])
    assert own.json()["code"] == "conversion_canonical"

    saved = client.put("/v1/admin/catalogue/hba1c/ranges", json=[{"sex": "unknown", "age_min": 18, "age_max": 120,
                                                                   "low": "4.0", "high": "5.7"}]).json()
    assert saved["ranges"] == [{"sex": "unknown", "age_min": 18, "age_max": 120, "low": "4.0", "high": "5.7"}]
    # a report that prints no range now gets the new one
    with sessions() as s:
        row = RawRow("HbA1c", "5.65", "%", None, None, None, 1.0, "manual")
        read = current_interpreter(s).interpret(row, "male", 58)
        assert (str(read.ref_high), read.ref_source) == ("5.7", "catalogue")
        actions = s.scalars(select(AuditLog.action).where(AuditLog.action.like("catalogue.%"))).all()
        assert actions == ["catalogue.ranges"]  # the refused changes left nothing behind


def test_a_critical_limit_applies_only_after_clinical_review(client: TestClient, staff, sessions) -> None:
    with sessions.begin() as s:
        p = Profile(owner_user_id=staff["family"].id, display_name="Ramesh", sex=Sex.MALE,
                    date_of_birth=date(1968, 3, 14))
        s.add(p)
        s.flush()
        r = add_report(s, p.id, staff["family"].id, date(2026, 8, 19), {"potassium": (5.8, 3.5, 5.1)})
        r.status = ReportStatus.EXPLAINED
        analyse_profile(s, p.id)
        obs_id = s.scalar(select(Observation.id).where(Observation.report_id == r.id))

    as_(staff["admin"])
    proposed = client.put("/v1/admin/catalogue/potassium/critical-limit",
                          json={"low": "2.8", "high": "5.5", "note": "Match the hospital's protocol"}).json()
    assert proposed["critical"]["high"] == "6.2"  # still the current limit
    assert proposed["critical"]["proposed"]["high"] == "5.5"
    assert proposed["critical"]["proposed"]["by"] == "admin@nabz.local"
    assert client.post("/v1/review/critical-limits/potassium", json={"approve": True}).status_code == 403
    with sessions() as s:
        assert s.get(Observation, obs_id).status is ObsStatus.HIGH

    as_(staff["reviewer"])
    queue = client.get("/v1/review/critical-limits").json()
    assert queue[0]["code"] == "potassium" and queue[0]["ranges"][0]["high"] == "5.1"
    assert client.patch("/v1/admin/catalogue/potassium", json={"decimals": 2}).status_code == 403
    decided = client.post("/v1/review/critical-limits/potassium", json={"approve": True, "note": "Agreed"}).json()
    assert decided["results_changed"] == 1
    assert decided["critical"]["high"] == "5.5" and decided["critical"]["reviewed_by"] == "reviewer@nabz.local"
    assert decided["critical"]["proposed"] is None
    with sessions() as s:
        assert s.get(Observation, obs_id).status is ObsStatus.CRITICAL_HIGH
        assert s.scalar(select(ProcessingJob.stage).where(ProcessingJob.report_id == r.id)) is JobStage.EXPLAIN

    # a proposal can be turned down, and the limit stays as it was
    as_(staff["admin"])
    client.put("/v1/admin/catalogue/potassium/critical-limit", json={"high": "9", "note": "Too many alerts"})
    as_(staff["reviewer"])
    rejected = client.post("/v1/review/critical-limits/potassium", json={"approve": False, "note": "Unsafe"}).json()
    assert rejected["critical"]["high"] == "5.5" and rejected["critical"]["proposed"] is None
    assert client.post("/v1/review/critical-limits/potassium", json={"approve": False}).json()["code"] == "no_proposal"
    as_(staff["admin"])
    history = client.get("/v1/admin/catalogue/potassium").json()["history"]
    assert [h["action"] for h in history] == ["catalogue.limit_rejected", "catalogue.limit_proposed",
                                              "catalogue.limit_approved", "catalogue.limit_proposed"]


def test_knowledge_documents_are_chunked_embedded_and_removed(client: TestClient, staff, sessions) -> None:
    as_(staff["admin"])
    text = ("# What it measures\n\nThe HbA1c test shows your average blood sugar over the past three months. "
            "It measures how much sugar is attached to haemoglobin.\n\n# Why it is done\n\n"
            "Doctors use it to check for diabetes and to see how well it is controlled.")
    body = {"title": "Hemoglobin A1C (HbA1c) Test", "source_org": "MedlinePlus", "url": KB_URL,
            "license": "Public domain (U.S. government work)", "test_code": "hba1c", "text": text}
    added = client.post("/v1/admin/knowledge", json=body)
    assert added.status_code == 201
    doc = added.json()
    assert (doc["chunks"], doc["tests"], doc["citations"]) == (2, ["hba1c"], 0)
    assert client.post("/v1/admin/knowledge", json=body).json()["code"] == "kb_duplicate"
    assert client.post("/v1/admin/knowledge", json={**body, "url": KB_URL + "x", "test_code": "nope"}).json()["code"] \
        == "unknown_test"

    overview = client.get("/v1/admin/knowledge").json()
    assert overview["embedder"] == "hash-bow (tests)" and any(d["id"] == doc["id"] for d in overview["documents"])
    assert client.post(f"/v1/admin/knowledge/{doc['id']}/reembed").json()["chunks"] == 2
    assert client.delete(f"/v1/admin/knowledge/{doc['id']}").status_code == 204
    assert all(d["id"] != doc["id"] for d in client.get("/v1/admin/knowledge").json()["documents"])

    app.dependency_overrides[get_embedder] = lambda: None  # without the model, nothing can be embedded
    assert client.post("/v1/admin/knowledge", json=body).json()["code"] == "embedder_unavailable"
    with sessions() as s:
        actions = s.scalars(select(AuditLog.action).where(AuditLog.action.like("knowledge.%"))).all()
        assert actions == ["knowledge.add", "knowledge.reembed", "knowledge.delete"]


def test_text_is_split_into_sections_and_passages() -> None:
    pieces = chunk_text("Title", "Intro one.\n\n# Part two\n\n" + "word " * 100 + "\n\n" + "more " * 50)
    assert pieces[0] == ("Title", "Intro one.")
    assert [section for section, _ in pieces[1:]] == ["Part two", "Part two"]  # 150 words: two passages
