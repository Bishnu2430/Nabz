"""Questions about a report (FR-27): ask, read the earlier ones again, delete one."""

from __future__ import annotations

import uuid
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_session, owned_report
from app.core.config import settings
from app.explain.llm import GroqProvider, LLMProvider
from app.knowledge.embed import Embedder, default_embedder
from app.models import AppUser, ReportQuestion
from app.models.enums import ReportStatus
from app.schemas import AskIn, QuestionOut
from app.services import audit
from app.services.ask import answer_question
from app.services.auth import RateLimiter

router = APIRouter(tags=["questions"])
ANALYSED = {ReportStatus.EXPLAINING, ReportStatus.EXPLAINED}
ask_limiter = RateLimiter(20, 60)  # per account: a conversation, not a crawl


@lru_cache(maxsize=1)
def _groq() -> LLMProvider | None:
    # Someone is waiting for the answer: one retry, then the rule-built answer.
    if not settings.groq_api_key:
        return None
    return GroqProvider(settings.groq_api_key, settings.llm_model, timeout=30.0, max_retries=1, max_wait=8.0)


def get_llm() -> LLMProvider | None:
    return _groq()


def get_embedder() -> Embedder | None:
    return default_embedder()


def _out(q: ReportQuestion) -> QuestionOut:
    return QuestionOut(id=q.id, language=q.language, question=q.question, answer=q.answer, mode=q.mode,
                       refusal=q.refusal, reason=(q.meta or {}).get("reason"), test_codes=q.test_codes or [],
                       sources=q.sources or [], created_at=q.created_at)


@router.post("/v1/reports/{report_id}/ask", response_model=QuestionOut, status_code=status.HTTP_201_CREATED)
def ask(report_id: uuid.UUID, body: AskIn, session: Session = Depends(get_session),  # noqa: B008
        user: AppUser = Depends(current_user), provider: LLMProvider | None = Depends(get_llm),  # noqa: B008
        embedder: Embedder | None = Depends(get_embedder)):  # noqa: B008
    report = owned_report(session, user, report_id)
    if report.status not in ANALYSED:
        raise HTTPException(status.HTTP_409_CONFLICT, "The report hasn't been analysed yet.")
    if not ask_limiter.allow(str(user.id)):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            {"detail": "Too many questions. Wait a minute and ask again.", "code": "too_many"})
    row = answer_question(session, report, user.id, body.question, body.language.value, provider, embedder)
    # what was asked stays out of the audit log; only that a question was asked and how it was handled
    audit.record(session, user.id, "report.ask", "report", report.id, mode=row.mode, refusal=row.refusal)
    session.commit()
    return _out(row)


@router.get("/v1/reports/{report_id}/questions", response_model=list[QuestionOut])
def list_questions(report_id: uuid.UUID, session: Session = Depends(get_session),  # noqa: B008
                   user: AppUser = Depends(current_user)):  # noqa: B008
    report = owned_report(session, user, report_id)
    rows = session.scalars(select(ReportQuestion).where(ReportQuestion.report_id == report.id)
                           .order_by(ReportQuestion.created_at.desc()).limit(50)).all()
    return [_out(q) for q in reversed(rows)]


@router.delete("/v1/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question(question_id: uuid.UUID, session: Session = Depends(get_session),  # noqa: B008
                    user: AppUser = Depends(current_user)):  # noqa: B008
    row = session.get(ReportQuestion, question_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found.")
    owned_report(session, user, row.report_id)
    session.delete(row)
    session.commit()
