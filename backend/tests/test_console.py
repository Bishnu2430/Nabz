"""The safety and admin console: who may see what, the reviewer's de-identified queue and verdicts, the checks
playground, the live red-team run, and the admin's users, jobs and audit log."""

import json
from collections.abc import Iterator
from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.api import deps
from app.core.security import UNUSABLE_PASSWORD_HASH
from app.explain.fixtures import payload
from app.explain.redteam import explanation_cases, question_cases, run_all
from app.explain.validator import annotate
from app.main import app
from app.models import AppUser, Explanation, Feedback, ProcessingJob, ReportQuestion
from app.models.enums import JobStage, JobStatus, ReportStatus, SafetyStatus, Sex, UserRole
from app.services.analysis import analyse_profile
from app.services.review import redact
from tests.factories import add_report, make_profile


def test_the_red_team_suites_pass_when_run_from_the_console() -> None:
    result = run_all()
    assert result["totals"] == {"explanation": {"cases": len(explanation_cases()), "passed": len(explanation_cases())},
                                "question": {"cases": len(question_cases()), "passed": len(question_cases())}}
    assert {r["suite"] for r in result["results"]} == {"explanation", "question"}


def test_annotate_marks_what_each_check_caught() -> None:
    text = "Your creatinine is 1.42 mg/dL. You have kidney disease. Take 500 mg of iron. Normal is under 1.1."
    checked, spans = annotate(text, payload(), "en")
    caught = {(checked[s["start"]:s["end"]], s["code"]) for s in spans}
    assert ("You have kidney", "diagnosis") in caught and ("500 mg", "treatment") in caught
    assert ("1.1", "number") in caught and ("500", "number") in caught
    assert not any(code == "number" and word == "1.42" for word, code in caught)  # it is in the report


def test_redact_removes_contact_details() -> None:
    assert redact("Mail me at asha.k@example.com or +91 98765 43210") == "Mail me at [email] or [number]"


db = pytest.mark.db  # the tests below need the database


@pytest.fixture
def people(sessions: sessionmaker[Session]) -> dict[str, AppUser]:
    made = {}
    with sessions.begin() as s:
        for name, role in (("member", UserRole.USER), ("reviewer", UserRole.REVIEWER), ("admin", UserRole.ADMIN)):
            u = AppUser(email=f"{name}@nabz.local", password_hash=UNUSABLE_PASSWORD_HASH, role=role,
                        email_verified_at=datetime.now(UTC),
                        totp_enabled_at=datetime.now(UTC) if role is not UserRole.USER else None)
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
def blocked(sessions: sessionmaker[Session]) -> dict:
    """A family member's report with a blocked explanation, a refused question and an unhelpful rating."""
    with sessions.begin() as s:
        p = make_profile(s, email="family@nabz.local")
        p.sex, p.date_of_birth, p.display_name = Sex.MALE, date(1980, 3, 1), "Ramesh Kumar"
        r = add_report(s, p.id, p.owner_user_id, date(2026, 5, 1), {
            "creatinine": (1.42, 0.72, 1.3), "hb": (12.1, 13.0, 17.0)})
        r.status = ReportStatus.EXPLAINED
        analyse_profile(s, p.id)
        rejected = {"model": "m", "content": {"summary": "You have kidney disease.", "per_test": [],
                                              "doctor_questions": []},
                    "problems": [{"code": "diagnosis", "detail": "'You have kidney'"}]}
        e = Explanation(report_id=r.id, language="en", model_id="template", prompt_version="explain-v5",
                        safety_status=SafetyStatus.FALLBACK,
                        content={"summary": "Creatinine is 1.42 mg/dL, above the lab's range.", "per_test": [],
                                 "doctor_questions": [], "meta": {"source": "template", "reason": "validation",
                                                                  "problems": ["diagnosis"], "rejected": rejected}})
        s.add(e)
        s.flush()
        q = ReportQuestion(report_id=r.id, user_id=p.owner_user_id, language="en", mode="refusal", refusal="diagnosis",
                           question="Do I have kidney disease? Call me on 98765 43210", answer="Nabz can't tell you.",
                           test_codes=["creatinine"], sources=[], meta={"reason": None, "problems": []})
        s.add(q)
        s.add(Feedback(explanation_id=e.id, user_id=p.owner_user_id, rating=-1, comment="Too vague"))
        s.flush()
        return {"report": r.id, "explanation": e.id, "question": q.id}


@db
def test_members_cannot_open_the_console(client: TestClient, people) -> None:
    as_(people["member"])
    for url in ("/v1/review/queue", "/v1/review/summary", "/v1/admin/overview", "/v1/admin/users"):
        r = client.get(url)
        assert r.status_code == 403 and r.json()["code"] == "forbidden", url
    as_(people["reviewer"])
    assert client.get("/v1/admin/users").status_code == 403  # users and roles are for admins
    assert client.get("/v1/admin/overview").status_code == 200 and client.get("/v1/admin/audit").status_code == 200
    as_(people["admin"])
    assert client.get("/v1/review/queue").status_code == 403  # the queue holds health values, de-identified or not


@db
def test_the_reviewer_sees_blocked_text_de_identified_and_records_a_verdict(client: TestClient, people,
                                                                             blocked) -> None:
    as_(people["reviewer"])
    items = client.get("/v1/review/queue").json()
    assert {i["kind"] for i in items} == {"explanation", "question", "feedback"}
    sent = json.dumps(items)
    assert "Ramesh" not in sent and "family@nabz.local" not in sent and "1980" not in sent
    assert "98765" not in sent and "[number]" in sent

    expl = next(i for i in items if i["kind"] == "explanation")
    assert expl["age_band"] == "40–49" and expl["sex"] == "male" and expl["reason"] == "validation"
    assert [v["test"] for v in expl["values"]] == ["Creatinine", "Haemoglobin"]
    marked = expl["blocked"]
    assert [marked["text"][s["start"]:s["end"]] for s in marked["spans"]] == ["You have kidney"]
    fb = next(i for i in items if i["kind"] == "feedback")
    assert fb["feedback"] == {"helpful": False, "comment": "Too vague"}

    made = client.post(f"/v1/review/items/explanation/{blocked['explanation']}",
                       json={"verdict": "correct", "note": "Rightly blocked"})
    assert made.status_code == 201 and made.json()["reviewer"] == "reviewer@nabz.local"
    assert {i["kind"] for i in client.get("/v1/review/queue").json()} == {"question", "feedback"}
    done = client.get("/v1/review/queue?state=reviewed").json()
    assert [(i["kind"], i["review"]["verdict"], i["review"]["note"]) for i in done] == [
        ("explanation", "correct", "Rightly blocked")]
    summary = client.get("/v1/review/summary").json()
    assert summary["open"] == {"explanation": 0, "question": 1, "feedback": 1}
    assert summary["refusals"] == {"diagnosis": 1}
    assert client.post(f"/v1/review/items/question/{blocked['explanation']}",
                       json={"verdict": "correct"}).status_code == 404


@db
def test_the_checks_playground_and_the_live_red_team_run(client: TestClient, people) -> None:
    as_(people["reviewer"])
    out = client.post("/v1/review/check", json={"text": "This suggests you have diabetes. Don't worry.",
                                                "language": "en"}).json()
    assert {p["code"] for p in out["problems"]} == {"diagnosis", "reassurance"}
    assert out["as_question"] is None
    assert client.post("/v1/review/check", json={"text": "What medicine should I take?"}).json()["as_question"] == \
        "treatment"
    run = client.post("/v1/review/redteam").json()
    assert all(t["cases"] == t["passed"] for t in run["totals"].values())


@db
def test_the_admin_manages_roles_sessions_and_failed_jobs(client: TestClient, people, blocked, sessions) -> None:
    as_(people["admin"])
    listed = {u["email"]: u for u in client.get("/v1/admin/users").json()}
    assert listed["family@nabz.local"]["profiles"] == 1 and listed["reviewer@nabz.local"]["totp"] is True
    member = listed["member@nabz.local"]["id"]
    made = client.patch(f"/v1/admin/users/{member}", json={"role": "reviewer"})
    assert made.status_code == 200 and made.json()["role"] == "reviewer"
    assert client.patch(f"/v1/admin/users/{people['admin'].id}", json={"role": "user"}).json()["code"] == "own_role"
    assert client.post(f"/v1/admin/users/{member}/unlock").status_code == 200
    assert client.post(f"/v1/admin/users/{member}/sign-out").json()["sessions"] == 0

    with sessions.begin() as s:
        job = ProcessingJob(report_id=blocked["report"], stage=JobStage.EXPLAIN, status=JobStatus.FAILED,
                            attempts=3, error="LLMError: HTTP 503")
        s.add(job)
    failed = client.get("/v1/admin/jobs?state=failed").json()
    assert [(j["stage"], j["error"]) for j in failed] == [("explain", "LLMError: HTTP 503")]
    again = client.post(f"/v1/admin/jobs/{failed[0]['id']}/retry").json()
    assert again["status"] == "queued" and again["error"] is None
    assert client.post(f"/v1/admin/jobs/{failed[0]['id']}/retry").status_code == 409

    actions = [a["action"] for a in client.get("/v1/admin/audit?action=admin.").json()]
    assert actions == ["admin.job_retry", "admin.sign_out", "admin.unlock", "admin.role"]
    overview = client.get("/v1/admin/overview").json()
    assert overview["health"]["database"] is True and overview["counts"]["people"] == 1
    assert len(overview["activity"]) == 14 and "Ramesh" not in json.dumps(overview)
    with sessions() as s:
        assert s.scalar(select(AppUser.role).where(AppUser.email == "member@nabz.local")) is UserRole.REVIEWER
