"""The clinical reviewer's console (FR-48): the safety queue, verdicts, a playground for the checks, and the
red-team suites run live. Reviewers only; every item is de-identified (app.services.review)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_session, require_roles
from app.explain.ask import gate
from app.explain.redteam import run_all
from app.explain.validator import annotate, banned
from app.models import AppUser, Explanation, Feedback, ReportQuestion, SafetyReview
from app.models.enums import UserRole
from app.schemas import CheckIn, CheckOut, ReviewItem, VerdictIn
from app.services import audit, review
from app.services.auth import RateLimiter

router = APIRouter(prefix="/v1/review", tags=["review"])
reviewer = require_roles(UserRole.REVIEWER)
redteam_limiter = RateLimiter(10, 60)
SUBJECTS = {"explanation": Explanation, "question": ReportQuestion, "feedback": Feedback}


@router.get("/summary")
def summary(session: Session = Depends(get_session), user: AppUser = Depends(reviewer)):  # noqa: B008
    return review.summary(session)


@router.get("/queue", response_model=list[ReviewItem])
def queue(kind: str | None = None, state: str = "open", session: Session = Depends(get_session),  # noqa: B008
          user: AppUser = Depends(reviewer)):  # noqa: B008
    if kind is not None and kind not in review.KINDS or state not in ("open", "reviewed", "all"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unknown kind or state.")
    return review.queue(session, kind, state)


@router.post("/items/{kind}/{item_id}", status_code=status.HTTP_201_CREATED)
def verdict(kind: str, item_id: uuid.UUID, body: VerdictIn, session: Session = Depends(get_session),  # noqa: B008
            user: AppUser = Depends(reviewer)):  # noqa: B008
    model = SUBJECTS.get(kind)
    if model is None or session.get(model, item_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found.")
    row = SafetyReview(subject_type=kind, subject_id=item_id, reviewer_id=user.id, verdict=body.verdict,
                       note=(body.note or "").strip() or None)
    session.add(row)
    audit.record(session, user.id, "review.verdict", kind, item_id, verdict=body.verdict)
    session.commit()
    return {"verdict": row.verdict, "note": row.note, "reviewer": user.email, "at": row.created_at}


@router.post("/check", response_model=CheckOut)
def check(body: CheckIn, user: AppUser = Depends(reviewer)):  # noqa: B008
    """Run the wording checks on any text, as if a model had written it, and the question gate as if someone had
    asked it. Numbers are checked against a report's own values, so they aren't checked here."""
    text, spans = annotate(body.text, None, body.language.value)
    problems = [{"code": p.code, "detail": p.detail} for p in banned(body.text, body.language.value)]
    return CheckOut(text=text, spans=spans, problems=problems, as_question=gate(body.text))


@router.post("/redteam")
def redteam(session: Session = Depends(get_session), user: AppUser = Depends(reviewer)):  # noqa: B008
    if not redteam_limiter.allow(str(user.id)):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, {"detail": "Wait a minute and run it again.",
                                                                "code": "too_many"})
    result = run_all()
    audit.record(session, user.id, "review.redteam", "suite", None,
                 **{suite: f"{t['passed']}/{t['cases']}" for suite, t in result["totals"].items()})
    session.commit()
    return result
