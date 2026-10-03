"""Answer a question about one report (FR-47, ADR-0013).

Order of events: rules decide whether the question may be answered at all (app.explain.ask). If it may, the model
writes the answer only with external-AI consent, a model and the knowledge base, and never around a critical value;
its answer is shown only if it passes the same deterministic checks as an explanation and the judge. In every other
case the answer is built by rules from the person's values and MedlinePlus. Each question is stored with what
happened, and a blocked model answer is kept for the clinical reviewer, never shown.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.explain.ask import (
    ASK_JUDGE_EXTRA,
    ASK_PROMPT_VERSION,
    ask_messages,
    ask_schema,
    knowledge_answer,
    refusal_text,
    understand,
    validate_answer,
)
from app.explain.llm import LLMError, LLMProvider
from app.explain.payload import build_items, make_payload
from app.explain.prompt import JUDGE_SCHEMA, JUDGE_SYSTEM
from app.explain.validator import Problem
from app.knowledge.embed import Embedder
from app.knowledge.retrieve import opening_passages, retrieve_for_question
from app.models import LabTest, Report, ReportQuestion
from app.models.enums import ConsentPurpose
from app.services.explanation import passage_sources
from app.services.ingest import has_consent

log = logging.getLogger("nabz.ask")


def test_names(session: Session) -> tuple[dict[str, list[str]], dict[str, str]]:
    """Every catalogue test's names (longest first, for matching in a question) and its display name."""
    names: dict[str, list[str]] = {}
    display: dict[str, str] = {}
    for code, name, short, aliases in session.execute(
            select(LabTest.code, LabTest.canonical_name, LabTest.short_name, LabTest.aliases)):
        names[code] = sorted({name, short, *(aliases or [])}, key=len, reverse=True)
        display[code] = name
    return names, display


def _judge_messages(payload_json: str, question: str, answer: str) -> list[dict[str, str]]:
    return [{"role": "system", "content": JUDGE_SYSTEM + ASK_JUDGE_EXTRA},
            {"role": "user", "content": f"DATA\n{payload_json}\n\nQUESTION\n{question}\n\nEXPLANATION\n{answer}"}]


def answer_question(session: Session, report: Report, user_id: uuid.UUID | None, question: str, language: str,
                    provider: LLMProvider | None, embedder: Embedder | None, judge: bool = True) -> ReportQuestion:
    question = " ".join(question.split())
    items, profile, band = build_items(session, report)
    names, display = test_names(session)
    asked = understand(question, items, names)
    focus = asked.tests or [i for i in items if i.is_focus]
    payload = make_payload(items, profile, band, focus)

    mode = "refusal"
    refusal = asked.refusal
    reason: str | None = None  # why rules, not the model, wrote the answer
    problems: list[Problem] = []
    rejected: dict | None = None
    answer: str | None = None
    used = []
    model_id: str | None = None
    tokens_in = tokens_out = latency = 0

    if refusal is None:
        if payload.critical:
            reason = "critical"  # no generated prose around a critical value
        elif not has_consent(session, report.profile_id, ConsentPurpose.EXTERNAL_AI):
            reason = "no_consent"
        elif provider is None:
            reason = "no_model"
        elif embedder is None:
            reason = "no_knowledge"
        if reason is None:
            passages = retrieve_for_question(session, embedder, asked.tests, question)
            try:
                done = provider.complete_json(ask_messages(payload, passages, question, language),
                                              ask_schema([p.label for p in passages]), "answer", effort="low",
                                              max_tokens=1500)
                tokens_in, tokens_out, latency = done.input_tokens, done.output_tokens, done.latency_ms
                model_id = done.model
                if done.content.get("answerable") is not True:
                    refusal = "cannot_answer"
                else:
                    problems = validate_answer(done.content, payload, passages, language)
                    if not problems and judge:
                        verdict = provider.complete_json(
                            _judge_messages(payload.to_json(), question, str(done.content.get("answer", ""))),
                            JUDGE_SCHEMA, "safety_review", effort="low", max_tokens=1500)
                        tokens_in += verdict.input_tokens
                        tokens_out += verdict.output_tokens
                        latency += verdict.latency_ms
                        if verdict.content.get("safe") is not True:
                            problems.append(Problem("judge", "; ".join(map(str, verdict.content.get("problems")
                                                                           or []))[:500]))
                    if problems:
                        reason = "validation"
                        rejected = {"model": done.model, "content": done.content,
                                    "problems": [{"code": p.code, "detail": p.detail} for p in problems]}
                    else:
                        answer, mode = str(done.content["answer"]).strip(), "model"
                        cited = set(done.content.get("citations") or [])
                        used = [p for p in passages if p.label in cited]
            except LLMError as exc:
                reason = "provider_error"
                problems = [Problem("provider", str(exc))]

    if refusal is not None:
        mode = "refusal"
        answer = refusal_text(refusal, asked, payload, language, [i.test for i in items],
                              [display.get(c, c) for c in asked.missing])
    elif answer is None:
        mode = "knowledge"
        passages = opening_passages(session, asked.tests)
        answer, labels = knowledge_answer(asked, payload, passages, language)
        used = [p for p in passages if p.label in labels]
        model_id = None

    if problems:
        log.info("answer for report %s (%s) came from rules: %s", report.id, language,
                 ",".join(sorted({p.code for p in problems})))
    row = ReportQuestion(
        report_id=report.id, user_id=user_id, language=language, question=question, answer=answer, mode=mode,
        refusal=refusal, test_codes=[t.test_code for t in asked.tests], sources=passage_sources(session, used),
        meta={"reason": reason, "problems": [p.code for p in problems], "rejected": rejected},
        model_id=model_id, prompt_version=ASK_PROMPT_VERSION if model_id else None,
        input_tokens=tokens_in or None, output_tokens=tokens_out or None, latency_ms=latency or None,
    )
    session.add(row)
    session.flush()
    return row
