"""Explanations, narration and feedback (FR-21 – FR-26)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_session, get_storage, owned_report
from app.core.config import settings
from app.explain.tts import ElevenLabsProvider, TTSError, TTSProvider, narration_text
from app.models import AppUser, Explanation, Feedback, ProcessingJob, Report
from app.models.enums import ConsentPurpose, JobStage, JobStatus, Lang, ReportStatus
from app.schemas import AudioOut, ExplainIn, ExplanationOut, ExplanationState, FeedbackIn
from app.services import audit
from app.services.ingest import has_consent
from app.storage import StorageBackend
from app.worker import queue

router = APIRouter(tags=["explanations"])
ANALYSED = {ReportStatus.EXPLAINING, ReportStatus.EXPLAINED}


def get_tts() -> TTSProvider | None:
    if not settings.elevenlabs_api_key:
        return None
    models = {"en": settings.elevenlabs_model, "hi": settings.elevenlabs_model, "or": settings.elevenlabs_model_or}
    return ElevenLabsProvider(settings.elevenlabs_api_key, models,
                              {"en": settings.elevenlabs_voice_en, "hi": settings.elevenlabs_voice_hi,
                               "or": settings.elevenlabs_voice_or})


def _out(e: Explanation) -> ExplanationOut:
    c = e.content
    meta = c.get("meta") or {}
    return ExplanationOut(
        id=e.id, language=e.language, source=meta.get("source", "template"), reason=meta.get("reason"),
        summary=c.get("summary", ""), per_test=c.get("per_test", []), doctor_questions=c.get("doctor_questions", []),
        disclaimer_key=c.get("disclaimer_key", ""), sources=c.get("sources", []), has_audio=e.audio_key is not None,
        created_at=e.created_at,
    )


def _pending(session: Session, report: Report, language: Lang) -> bool:
    jobs = session.scalars(select(ProcessingJob).where(
        ProcessingJob.report_id == report.id, ProcessingJob.stage == JobStage.EXPLAIN,
        ProcessingJob.status.in_([JobStatus.QUEUED, JobStatus.RUNNING]))).all()
    return any((j.args or {}).get("lang", language.value) == language.value for j in jobs)


def _owned_explanation(session: Session, user: AppUser, explanation_id: uuid.UUID) -> Explanation:
    e = session.get(Explanation, explanation_id)
    if e is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Explanation not found.")
    owned_report(session, user, e.report_id)
    return e


@router.get("/v1/reports/{report_id}/explanation", response_model=ExplanationState)
def get_explanation(report_id: uuid.UUID, lang: Lang = Lang.EN, session: Session = Depends(get_session),  # noqa: B008
                    user: AppUser = Depends(current_user)):  # noqa: B008
    report = owned_report(session, user, report_id)
    e = session.scalar(select(Explanation).where(Explanation.report_id == report.id, Explanation.language == lang)
                       .order_by(Explanation.created_at.desc()))
    if _pending(session, report, lang):
        return ExplanationState(state="pending", explanation=_out(e) if e else None)
    return ExplanationState(state="ready" if e else "none", explanation=_out(e) if e else None)


@router.post("/v1/reports/{report_id}/explanation", response_model=ExplanationState,
             status_code=status.HTTP_202_ACCEPTED)
def request_explanation(report_id: uuid.UUID, body: ExplainIn, session: Session = Depends(get_session),  # noqa: B008
                        user: AppUser = Depends(current_user)):  # noqa: B008
    """Queue an explanation in another language, or a fresh one (e.g. after external-AI consent is given)."""
    report = owned_report(session, user, report_id)
    if report.status not in ANALYSED:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            {"detail": "The report hasn't been analysed yet.", "code": "not_analysed"})
    exists = session.scalar(select(Explanation.id).where(Explanation.report_id == report.id,
                                                        Explanation.language == body.language))
    if (exists and not body.regenerate) or _pending(session, report, body.language):
        return get_explanation(report_id, body.language, session, user)
    queue.enqueue(session, report.id, JobStage.EXPLAIN, args={"lang": body.language.value})
    audit.record(session, user.id, "explanation.request", "report", report.id, language=body.language.value)
    session.commit()
    return ExplanationState(state="pending")


@router.post("/v1/explanations/{explanation_id}/audio", response_model=AudioOut)
def narrate(explanation_id: uuid.UUID, session: Session = Depends(get_session),  # noqa: B008
            user: AppUser = Depends(current_user), storage: StorageBackend = Depends(get_storage),  # noqa: B008
            tts: TTSProvider | None = Depends(get_tts)):  # noqa: B008
    """Generate the narration on the first press of play (voice consent needed), then reuse it."""
    e = _owned_explanation(session, user, explanation_id)
    url = f"/v1/explanations/{e.id}/audio"
    if e.audio_key:
        return AudioOut(url=url)
    report = session.get(Report, e.report_id)
    if not has_consent(session, report.profile_id, ConsentPurpose.VOICE):
        raise HTTPException(status.HTTP_409_CONFLICT, {"detail": "Narration needs consent to voice processing.",
                                                       "consent": "voice"})
    if tts is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Narration isn't configured.")
    try:
        audio = tts.synthesize(narration_text(e.content, e.language.value), e.language.value)
    except TTSError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "The narration service didn't respond. Try again.") from exc
    key = f"audio/{e.report_id}/{e.id}.mp3"
    storage.put(key, audio)
    e.audio_key = key
    audit.record(session, user.id, "explanation.narrate", "explanation", e.id, bytes=len(audio))
    session.commit()
    return AudioOut(url=url)


@router.get("/v1/explanations/{explanation_id}/audio")
def audio(explanation_id: uuid.UUID, session: Session = Depends(get_session),  # noqa: B008
          user: AppUser = Depends(current_user), storage: StorageBackend = Depends(get_storage)):  # noqa: B008
    e = _owned_explanation(session, user, explanation_id)
    if not e.audio_key:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No narration yet.")
    return Response(storage.get(e.audio_key), media_type="audio/mpeg",
                    headers={"Cache-Control": "private, max-age=86400"})


@router.post("/v1/explanations/{explanation_id}/feedback", status_code=status.HTTP_201_CREATED)
def feedback(explanation_id: uuid.UUID, body: FeedbackIn, session: Session = Depends(get_session),  # noqa: B008
             user: AppUser = Depends(current_user)):  # noqa: B008
    e = _owned_explanation(session, user, explanation_id)
    session.add(Feedback(explanation_id=e.id, user_id=user.id, rating=1 if body.helpful else -1, comment=body.comment))
    session.commit()
    return {"ok": True}
