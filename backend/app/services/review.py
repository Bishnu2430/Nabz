"""The clinical reviewer's safety queue (FR-48, docs/12 §2): what the checks blocked, what Nabz refused to answer,
and explanations readers found unhelpful, each with the reviewer's verdict.

Everything here is de-identified: an age band and sex, the test values, and the text involved. Never a name, an
email, a date of birth, a report file or the dates on it. What a person typed (a question, a feedback comment) is
shown with email addresses and phone numbers removed.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.explain.payload import Payload, build_items, build_payload, make_payload
from app.explain.validator import annotate, texts
from app.models import AppUser, Explanation, Feedback, Report, ReportQuestion, SafetyReview

KINDS = ("explanation", "question", "feedback")
BLOCKED_REASONS = ("validation", "provider_error")

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
_PHONE = re.compile(r"\+?\d[\d\s-]{6,}\d")


def redact(text: str | None) -> str | None:
    """What a person typed, without the details that most often identify them."""
    if text is None:
        return None
    return _PHONE.sub("[number]", _EMAIL.sub("[email]", text))


@dataclass
class Subject:
    kind: str
    id: uuid.UUID
    created_at: datetime
    report_id: uuid.UUID


def _subjects(session: Session, kind: str | None, limit: int) -> list[Subject]:
    found: list[Subject] = []
    if kind in (None, "explanation"):
        reason = Explanation.content["meta"]["reason"].astext
        found += [Subject("explanation", e.id, e.created_at, e.report_id) for e in session.scalars(
            select(Explanation).where(reason.in_(BLOCKED_REASONS)).order_by(Explanation.created_at.desc()).limit(limit))]
    if kind in (None, "question"):
        found += [Subject("question", q.id, q.created_at, q.report_id) for q in session.scalars(
            select(ReportQuestion).where(or_(ReportQuestion.refusal.is_not(None),
                                             ReportQuestion.meta["reason"].astext.in_(BLOCKED_REASONS)))
            .order_by(ReportQuestion.created_at.desc()).limit(limit))]
    if kind in (None, "feedback"):
        found += [Subject("feedback", f.id, f.created_at, e.report_id) for f, e in session.execute(
            select(Feedback, Explanation).join(Explanation, Explanation.id == Feedback.explanation_id)
            .where(Feedback.rating < 0).order_by(Feedback.created_at.desc()).limit(limit))]
    return sorted(found, key=lambda s: s.created_at, reverse=True)


def latest_reviews(session: Session, ids: list[uuid.UUID]) -> dict[uuid.UUID, dict[str, Any]]:
    if not ids:
        return {}
    rows = session.execute(
        select(SafetyReview, AppUser.email).outerjoin(AppUser, AppUser.id == SafetyReview.reviewer_id)
        .where(SafetyReview.subject_id.in_(ids)).order_by(SafetyReview.created_at)).all()
    return {r.subject_id: {"verdict": r.verdict, "note": r.note, "reviewer": email, "at": r.created_at}
            for r, email in rows}


def _values(payload: Payload) -> list[dict[str, Any]]:
    return [{"test": t.test, "value": t.value, "unit": t.unit, "range_low": t.range_low, "range_high": t.range_high,
             "status": t.status} for t in payload.focus]


def _explanation_text(content: dict) -> str:
    return "\n".join(t for t in texts(content) if t)


def _marked(text: str | None, payload: Payload | None, language: str) -> dict[str, Any] | None:
    if not text:
        return None
    checked, spans = annotate(text, payload, language)
    return {"text": checked, "spans": spans}


def _item(session: Session, subject: Subject) -> dict[str, Any] | None:
    report = session.get(Report, subject.report_id)
    if report is None:
        return None
    base = {"kind": subject.kind, "id": subject.id, "created_at": subject.created_at}
    if subject.kind in ("explanation", "feedback"):
        if subject.kind == "feedback":
            fb = session.get(Feedback, subject.id)
            explanation = session.get(Explanation, fb.explanation_id)
            feedback = {"helpful": fb.rating > 0, "comment": redact(fb.comment)}
        else:
            explanation, feedback = session.get(Explanation, subject.id), None
        payload = build_payload(session, report)
        meta = explanation.content.get("meta") or {}
        rejected = meta.get("rejected") or {}
        language = explanation.language.value
        return {**base, "language": language, "age_band": payload.age_band, "sex": payload.sex,
                "values": _values(payload), "question": None, "feedback": feedback,
                "shown": _explanation_text(explanation.content),
                "blocked": _marked(_explanation_text(rejected["content"]), payload, language)
                if rejected.get("content") else None,
                "problems": rejected.get("problems") or [{"code": c, "detail": ""} for c in meta.get("problems", [])],
                "reason": meta.get("reason"), "refusal": None, "mode": meta.get("source")}
    q = session.get(ReportQuestion, subject.id)
    items, profile, band = build_items(session, report)
    asked = [i for i in items if i.test_code in (q.test_codes or [])]
    payload = make_payload(items, profile, band, asked or [i for i in items if i.is_focus])
    rejected = (q.meta or {}).get("rejected") or {}
    language = q.language.value
    return {**base, "language": language, "age_band": payload.age_band, "sex": payload.sex,
            "values": _values(payload), "question": redact(q.question), "feedback": None, "shown": q.answer,
            "blocked": _marked(str((rejected.get("content") or {}).get("answer", "")), payload, language)
            if rejected else None,
            "problems": rejected.get("problems")
            or [{"code": c, "detail": ""} for c in (q.meta or {}).get("problems", [])],
            "reason": (q.meta or {}).get("reason"), "refusal": q.refusal, "mode": q.mode}


def queue(session: Session, kind: str | None = None, state: str = "open", limit: int = 40) -> list[dict[str, Any]]:
    subjects = _subjects(session, kind, limit * 3)
    reviews = latest_reviews(session, [s.id for s in subjects])
    out = []
    for s in subjects:
        review = reviews.get(s.id)
        if (state == "open" and review) or (state == "reviewed" and not review):
            continue
        if (item := _item(session, s)) is not None:
            out.append({**item, "review": review})
        if len(out) == limit:
            break
    return out


def summary(session: Session) -> dict[str, Any]:
    """How the checks are doing: explanations by source and reason, replies by mode, feedback, and what is open."""
    source = Explanation.content["meta"]["source"].astext
    reason = Explanation.content["meta"]["reason"].astext
    explanations = {k or "unknown": n for k, n in session.execute(select(source, func.count()).group_by(source))}
    reasons = {k or "none": n for k, n in session.execute(
        select(reason, func.count()).where(source == "template").group_by(reason))}
    modes = dict(session.execute(select(ReportQuestion.mode, func.count()).group_by(ReportQuestion.mode)).all())
    refusals = {k: n for k, n in session.execute(
        select(ReportQuestion.refusal, func.count()).where(ReportQuestion.refusal.is_not(None))
        .group_by(ReportQuestion.refusal))}
    ratings = dict(session.execute(select(Feedback.rating, func.count()).group_by(Feedback.rating)).all())
    helpful = {True: sum(n for r, n in ratings.items() if r > 0), False: sum(n for r, n in ratings.items() if r <= 0)}
    subjects = _subjects(session, None, 500)
    reviewed = latest_reviews(session, [s.id for s in subjects])
    attempts = explanations.get("model", 0) + reasons.get("validation", 0)
    return {
        "explanations": explanations, "fallback_reasons": reasons,
        "blocked_rate": round(reasons.get("validation", 0) / attempts, 3) if attempts else None,
        "questions": modes, "refusals": refusals,
        "feedback": {"helpful": helpful.get(True, 0), "not_helpful": helpful.get(False, 0)},
        "open": {k: sum(1 for s in subjects if s.kind == k and s.id not in reviewed) for k in KINDS},
        "reviewed": len(reviewed),
    }
