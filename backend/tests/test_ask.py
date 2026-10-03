"""Questions about a report: what the rules refuse, what they answer themselves, and when the model's answer is
shown. Rules are tested without a database; the service runs on a real one with a scripted model (no network)."""

import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.api import deps
from app.api.routes import ask as ask_routes
from app.core.config import settings
from app.explain.ask import Asked, gate, general_sentences, knowledge_answer, understand, validate_answer
from app.explain.llm import Completion, LLMError
from app.knowledge.embed import HashEmbedder
from app.knowledge.store import load_knowledge
from app.main import app
from app.models import AppUser, AuditLog, Consent, Observation, Report, ReportQuestion
from app.models.enums import ConsentPurpose, ReportStatus, Sex
from app.services.analysis import analyse_profile
from app.services.ask import answer_question
from tests.explain_fixtures import passages, payload
from tests.factories import add_report, make_profile

EMBED = HashEmbedder()
NAMES = {"creatinine": ["Serum Creatinine", "Creatinine"], "hb": ["Haemoglobin", "Hemoglobin", "Hb"],
         "tsh": ["Thyroid Stimulating Hormone", "TSH"], "sodium": ["Sodium", "Na"]}


# --- Rules -----------------------------------------------------------------------------------------------------------

QUESTIONS = [json.loads(line) for line in
             (Path(settings.data_dir) / "redteam" / "questions.jsonl").read_text(encoding="utf-8").splitlines() if line]


def test_the_question_suite_is_big_enough() -> None:
    refused = [c for c in QUESTIONS if c["expect"] != "answer"]
    assert len(refused) >= 40 and len(QUESTIONS) - len(refused) >= 10
    assert len({c["id"] for c in QUESTIONS}) == len(QUESTIONS)
    assert {c["expect"] for c in refused} == {"diagnosis", "treatment", "emergency", "instruction"}


@pytest.mark.parametrize("case", QUESTIONS, ids=[c["id"] for c in QUESTIONS])
def test_question(case: dict) -> None:
    """Red-team questions (data/redteam/questions.jsonl): each gets the fixed reply it should, or none."""
    assert gate(case["question"]) == (None if case["expect"] == "answer" else case["expect"])


def test_a_question_is_matched_to_the_tests_it_names() -> None:
    items = payload().focus
    asked = understand("What does my Creatinine and hb result mean?", items, NAMES)
    assert asked.refusal is None and [t.test_code for t in asked.tests] == ["creatinine", "hb"]
    assert [t.test_code for t in understand("How are my kidney tests?", items, NAMES).tests] == ["creatinine"]
    overview = understand("Which results are outside the range?", items, NAMES)
    assert overview.overview and [t.test_code for t in overview.tests] == ["creatinine", "hb"]
    assert understand("What is my TSH?", items, NAMES) == Asked("not_in_report", [], missing=("tsh",))
    assert understand("What is the weather in Cuttack?", items, NAMES).refusal == "off_topic"
    # a refusal still knows which test was meant, so the reply can show that result
    refused = understand("Do I have kidney disease because of my creatinine?", items, NAMES)
    assert refused.refusal == "diagnosis" and [t.test_code for t in refused.tests] == ["creatinine"]


def test_only_plain_sentences_about_the_test_are_quoted() -> None:
    text = ("What is a creatinine test?\nThis test measures creatinine in your blood. Creatinine is a waste product "
            "made by your muscles. Normal levels are 0.7 to 1.3 mg/dL. High levels may be a sign of kidney disease. "
            "Your kidneys filter it out of your blood.")
    assert general_sentences(text) == ("This test measures creatinine in your blood. Creatinine is a waste product "
                                       "made by your muscles.")
    assert general_sentences("High levels may mean kidney failure. You may need treatment.") == ""


def test_the_rule_built_answer_states_the_result_exactly() -> None:
    p = payload()
    asked = Asked(None, [p.focus[0]])
    text, used = knowledge_answer(asked, p, passages(), "en")
    assert text.startswith("Creatinine is 1.42 mg/dL, above the lab's range (0.72–1.3). That is 15 % higher than "
                           "12 months ago, more than normal day-to-day variation. It has been rising over the last "
                           "4 years.")
    assert text.endswith("Please talk to your doctor about these results.") and used == []  # the passage names a cause
    hindi, _ = knowledge_answer(asked, p, passages(), "hi")
    assert hindi.startswith("Creatinine 1.42 mg/dL है, लैब की सीमा (0.72–1.3) से अधिक।")


@pytest.mark.parametrize(("answer", "code"), [
    ("Your creatinine is 1.42 mg/dL, above the lab's range. You have kidney disease.", "diagnosis"),
    ("Your creatinine is 1.42 mg/dL. Take 500 mg of a supplement daily and talk to your doctor.", "treatment"),
    ("Your creatinine is 1.42 mg/dL, but there is nothing to worry about. Talk to your doctor.", "reassurance"),
    ("Your creatinine is 1.9 mg/dL, above the lab's range. Your doctor can tell what it means.", "number"),
    ("As P1 says, creatinine is a waste product. Your doctor can tell what it means for you.", "label"),
    ("Short.", "length"),
])
def test_a_model_answer_is_checked_like_an_explanation(answer: str, code: str) -> None:
    content = {"language": "en", "answerable": True, "answer": answer, "citations": ["P1"]}
    assert code in {p.code for p in validate_answer(content, payload(), passages(), "en")}


def test_a_good_model_answer_passes() -> None:
    content = {"language": "en", "answerable": True, "citations": ["P1"],
               "answer": "Creatinine is a waste product that your kidneys filter out of the blood. Your result is "
                         "1.42 mg/dL, above the lab's range of 0.72 to 1.3. A high result can have several causes. "
                         "Your doctor can tell what this means for you."}
    assert validate_answer(content, payload(), passages(), "en") == []


# --- The service, on a database --------------------------------------------------------------------------------------

class AnswerProvider:
    """A model double: answers with the given text, and judges as told."""

    model = "fn-model"

    def __init__(self, answer: str = "", answerable: bool = True, judge_safe: bool = True, fail: bool = False):
        self.answer, self.answerable, self.judge_safe, self.fail = answer, answerable, judge_safe, fail
        self.calls: list[tuple[str, list[dict]]] = []

    def complete_json(self, messages, schema, name, *, effort="medium", max_tokens=4000) -> Completion:  # noqa: ANN001
        self.calls.append((name, messages))
        if self.fail:
            raise LLMError("HTTP 503")
        if name == "safety_review":
            return Completion({"safe": self.judge_safe, "problems": [] if self.judge_safe else ["diagnoses"]},
                              self.model, 40, 10, 3)
        labels = schema["properties"]["citations"]["items"]["enum"]
        return Completion({"language": "en", "answerable": self.answerable, "answer": self.answer,
                           "citations": labels[:1]}, self.model, 300, 80, 900)


GOOD = ("Creatinine is a waste product that your kidneys filter out of the blood. Your result is 1.42 mg/dL, above "
        "the lab's range of 0.72 to 1.3. Your doctor can tell what this means for you.")


@pytest.fixture
def report(sessions: sessionmaker[Session], tmp_path: Path) -> tuple:
    rows = [{"test_code": code, "url": f"https://medlineplus.gov/lab-tests/{code}", "title": f"{code} test",
             "section": section, "text": text, "source_org": "US National Library of Medicine, MedlinePlus",
             "license": "Public domain", "language": "en", "retrieved_at": "2026-09-29", "sha256": "x"}
            for code, section, text in [
                ("creatinine", "What is it?", "A creatinine test measures the level of creatinine in your blood. "
                                              "Creatinine is a waste product made by your muscles."),
                ("creatinine", "What do the results mean?", "High creatinine may mean the kidneys are not working "
                                                            "well."),
                ("hb", "What is it?", "A hemoglobin test measures the protein in red blood cells that carries "
                                      "oxygen.")]]
    path = tmp_path / "chunks.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    with sessions.begin() as s:
        load_knowledge(s, EMBED, path)
        p = make_profile(s)
        p.sex, p.date_of_birth, p.display_name = Sex.MALE, date(1980, 3, 1), "Ramesh Kumar"
        r = add_report(s, p.id, p.owner_user_id, date(2026, 5, 1), {
            "creatinine": (1.42, 0.72, 1.3), "hb": (12.1, 13.0, 17.0), "sodium": (139, 135, 145)})
        for o in s.scalars(select(Observation).where(Observation.report_id == r.id)):
            o.unit = {"creatinine": "mg/dL", "hb": "g/dL", "sodium": "mmol/L"}[o.raw_name]
        r.status = ReportStatus.EXPLAINING
        analyse_profile(s, p.id)
        return p.id, p.owner_user_id, r.id


def consent(sessions, report) -> None:
    with sessions.begin() as s:
        s.add(Consent(user_id=report[1], profile_id=report[0], purpose=ConsentPurpose.EXTERNAL_AI,
                      policy_version="test"))


def ask(sessions, report, question: str, provider=None, language: str = "en") -> ReportQuestion:
    with sessions.begin() as s:
        row = answer_question(s, s.get(Report, report[2]), report[1], question, language, provider, EMBED)
        s.expunge(row)
        return row


db = pytest.mark.db  # the tests below need the database; the rules above do not


@db
def test_without_consent_rules_answer_and_nothing_leaves(sessions, report) -> None:
    provider = AnswerProvider(GOOD)
    row = ask(sessions, report, "What does creatinine measure?", provider)
    assert row.mode == "knowledge" and row.meta["reason"] == "no_consent" and provider.calls == []
    assert row.answer.splitlines() == [
        "Creatinine is 1.42 mg/dL, above the lab's range (0.72–1.3).",
        "About the test (MedlinePlus): A creatinine test measures the level of creatinine in your blood. Creatinine "
        "is a waste product made by your muscles.",
        "Please talk to your doctor about these results."]
    assert row.sources[0]["url"] == "https://medlineplus.gov/lab-tests/creatinine" and row.test_codes == ["creatinine"]


@db
def test_with_consent_a_checked_model_answer_is_shown(sessions, report) -> None:
    consent(sessions, report)
    provider = AnswerProvider(GOOD)
    row = ask(sessions, report, "What does  creatinine\nmeasure?", provider)
    assert row.mode == "model" and row.answer == GOOD and row.model_id == "fn-model" and row.refusal is None
    assert [name for name, _ in provider.calls] == ["answer", "safety_review"]
    assert row.question == "What does creatinine measure?" and row.input_tokens == 340
    sent = provider.calls[0][1][1]["content"]
    assert "Ramesh" not in sent and "2026" not in sent and sent.endswith("QUESTION\nWhat does creatinine measure?")


@db
@pytest.mark.parametrize(("provider", "problem"), [
    (AnswerProvider(GOOD + " You may have kidney disease."), "diagnosis"),
    (AnswerProvider(GOOD + " Normal is under 1.1."), "number"),
    (AnswerProvider(GOOD, judge_safe=False), "judge"),
])
def test_a_blocked_model_answer_is_kept_for_review_and_rules_answer(sessions, report, provider, problem) -> None:
    consent(sessions, report)
    row = ask(sessions, report, "What does creatinine measure?", provider)
    assert row.mode == "knowledge" and row.meta["reason"] == "validation" and problem in row.meta["problems"]
    assert row.meta["rejected"]["content"]["answer"] == provider.answer
    assert "kidney disease" not in row.answer and "1.1" not in row.answer


@db
def test_a_model_outage_or_a_declined_question_still_gets_a_reply(sessions, report) -> None:
    consent(sessions, report)
    down = ask(sessions, report, "What does creatinine measure?", AnswerProvider(fail=True))
    assert down.mode == "knowledge" and down.meta["reason"] == "provider_error"
    declined = ask(sessions, report, "Tell me about creatinine and the moon", AnswerProvider(answerable=False))
    assert declined.mode == "refusal" and declined.refusal == "cannot_answer"
    assert declined.answer == "Nabz can't answer that from this report. Your doctor can."


@db
def test_refusals_never_reach_the_model_and_show_the_report_instead(sessions, report) -> None:
    consent(sessions, report)
    provider = AnswerProvider(GOOD)
    dx = ask(sessions, report, "Do I have kidney disease?", provider)
    assert dx.mode == "refusal" and dx.refusal == "diagnosis" and provider.calls == []
    assert dx.answer.splitlines() == [
        "Nabz can't tell you whether you have a condition, how serious a result is, or what will happen. Only a "
        "doctor who knows you can.",
        "What the report shows:",
        "• Creatinine is 1.42 mg/dL, above the lab's range (0.72–1.3).",
        "• Sodium is 139 mmol/L, within the lab's range (135–145).",  # "kidney" means every kidney test in the report
        "Please talk to your doctor about these results."]
    rx = ask(sessions, report, "How can I increase my haemoglobin?", provider)
    assert rx.refusal == "treatment" and "• Haemoglobin is 12.1 g/dL, below the lab's range (13–17)." in rx.answer
    assert ask(sessions, report, "I have chest pain", provider).answer.startswith("If you feel very unwell")
    assert ask(sessions, report, "What is my TSH?", provider).answer.startswith("This report has no result for")
    off = ask(sessions, report, "Who won the match yesterday?", provider)
    assert off.refusal == "off_topic" and "for example: Creatinine, Haemoglobin or Sodium" in off.answer
    assert provider.calls == []


@db
def test_an_overview_lists_each_result_outside_its_range(sessions, report) -> None:
    row = ask(sessions, report, "Which results are outside the range?")
    assert row.mode == "knowledge" and row.test_codes == ["creatinine", "hb"]
    assert row.answer.splitlines()[:2] == ["Creatinine is 1.42 mg/dL, above the lab's range (0.72–1.3).",
                                           "Haemoglobin is 12.1 g/dL, below the lab's range (13–17)."]


# --- The API ---------------------------------------------------------------------------------------------------------

@db
def test_asking_listing_and_deleting_through_the_api(sessions, report) -> None:
    with sessions() as s:
        owner = s.get(AppUser, report[1])
        owner.email_verified_at = datetime.now(UTC)
        s.commit()
        s.refresh(owner)
        s.expunge(owner)
    with sessions.begin() as s:
        stranger = AppUser(email="mallory@nabz.local", password_hash="x", email_verified_at=datetime.now(UTC))  # noqa: S106
        s.add(stranger)
    app.dependency_overrides[deps.get_sessionmaker] = lambda: sessions
    app.dependency_overrides[deps.current_user] = lambda: owner
    app.dependency_overrides[ask_routes.get_llm] = lambda: None
    app.dependency_overrides[ask_routes.get_embedder] = lambda: EMBED
    try:
        with TestClient(app) as client:
            url = f"/v1/reports/{report[2]}/ask"
            assert client.post(url, json={"question": "hi"}).status_code == 422
            made = client.post(url, json={"question": "Do I have kidney disease?", "language": "en"})
            assert made.status_code == 201
            assert made.json()["refusal"] == "diagnosis" and made.json()["mode"] == "refusal"
            answered = client.post(url, json={"question": "What does creatinine measure?"}).json()
            assert answered["mode"] == "knowledge" and answered["reason"] == "no_consent"
            assert answered["sources"][0]["organisation"].endswith("MedlinePlus")
            listed = client.get(f"/v1/reports/{report[2]}/questions").json()
            assert [q["question"] for q in listed] == ["Do I have kidney disease?", "What does creatinine measure?"]
            export = client.get(f"/v1/profiles/{report[0]}/export").json()
            assert export["reports"][0]["questions"][0]["answered_by"] == "refusal"

            app.dependency_overrides[deps.current_user] = lambda: stranger
            assert client.post(url, json={"question": "What does creatinine measure?"}).status_code == 404
            assert client.get(f"/v1/reports/{report[2]}/questions").status_code == 404
            assert client.delete(f"/v1/questions/{answered['id']}").status_code == 404
            app.dependency_overrides[deps.current_user] = lambda: owner
            assert client.delete(f"/v1/questions/{answered['id']}").status_code == 204
    finally:
        app.dependency_overrides.clear()
    with sessions() as s:
        assert len(s.scalars(select(ReportQuestion)).all()) == 1
        logged = s.scalars(select(AuditLog).where(AuditLog.action == "report.ask")).all()
        # the audit log says a question was asked and how it was handled, never what was asked
        assert [e.meta for e in logged] == [{"mode": "refusal", "refusal": "diagnosis"},
                                            {"mode": "knowledge", "refusal": None}]
