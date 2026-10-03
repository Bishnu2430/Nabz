"""Running the system (FR-49, docs/12 §2): health, counts and activity, the job monitor and the audit log for staff;
users and roles, unlocking, signing out and retrying jobs for admins only.

The admin role runs the system without routine access to health data: nothing here returns a name, a value or a
report file. Accounts are listed by email, people only as a count.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import case, cast, func, select, text
from sqlalchemy.orm import Session
from sqlalchemy.types import Date

from app.api.deps import get_session, require_roles
from app.core.config import settings
from app.knowledge.embed import MODEL_DIR
from app.models import (
    AppUser,
    AuditLog,
    Explanation,
    HealthRecord,
    HomeReading,
    KbChunk,
    LabTest,
    ProcessingJob,
    Profile,
    Reminder,
    Report,
    ReportQuestion,
    ShareLink,
    UserSession,
)
from app.models.enums import JobStatus, UserRole
from app.schemas import AdminUserOut, AuditOut, JobOut, RoleIn
from app.services import audit
from app.services.auth import revoke_all
from app.worker.runner import RETRY_STATUS

router = APIRouter(prefix="/v1/admin", tags=["admin"])
staff = require_roles(UserRole.REVIEWER, UserRole.ADMIN)
admin = require_roles(UserRole.ADMIN)


def _by(session: Session, column, *where) -> dict[str, int]:  # noqa: ANN001
    q = select(column, func.count()).group_by(column)
    for w in where:
        q = q.where(w)
    return {str(getattr(k, "value", k)): n for k, n in session.execute(q)}


@router.get("/overview")
def overview(session: Session = Depends(get_session), user: AppUser = Depends(staff)):  # noqa: B008
    now = datetime.now(UTC)
    since = (now - timedelta(days=13)).date()

    def per_day(column) -> dict[str, int]:  # noqa: ANN001
        day = cast(column, Date)
        return {d.isoformat(): n for d, n in session.execute(
            select(day, func.count()).where(day >= since).group_by(day))}

    uploads, explanations, questions = per_day(Report.created_at), per_day(Explanation.created_at), \
        per_day(ReportQuestion.created_at)
    days = [(since + timedelta(days=i)).isoformat() for i in range(14)]
    last_job = session.scalar(select(func.max(ProcessingJob.finished_at)))
    try:
        session.execute(text("select 1"))
        database = True
    except Exception:  # noqa: BLE001 - a health check reports, it doesn't raise
        database = False
    return {
        "health": {
            "database": database,
            "worker_last_job": last_job,
            "jobs": _by(session, ProcessingJob.status),
            "model": bool(settings.groq_api_key),
            "voice": bool(settings.elevenlabs_api_key),
            "embeddings": (Path(settings.data_dir) / MODEL_DIR / "onnx" / "model_quantized.onnx").exists(),
            "mail": settings.mail_backend,
        },
        "counts": {
            "users": _by(session, AppUser.role, AppUser.deleted_at.is_(None)),
            "verified": session.scalar(select(func.count()).where(AppUser.email_verified_at.is_not(None))),
            "two_step": session.scalar(select(func.count()).where(AppUser.totp_enabled_at.is_not(None))),
            "people": session.scalar(select(func.count()).select_from(Profile).where(Profile.deleted_at.is_(None))),
            "reports": _by(session, Report.status, Report.deleted_at.is_(None)),
            "records": session.scalar(select(func.count()).select_from(HealthRecord)),
            "readings": session.scalar(select(func.count()).select_from(HomeReading)),
            "reminders": session.scalar(select(func.count()).select_from(Reminder).where(Reminder.done_at.is_(None))),
            "share_links": session.scalar(select(func.count()).select_from(ShareLink).where(
                ShareLink.revoked_at.is_(None), ShareLink.expires_at > now)),
            "explanations": _by(session, Explanation.content["meta"]["source"].astext),
            "questions": _by(session, ReportQuestion.mode),
            "tests": session.scalar(select(func.count()).select_from(LabTest)),
            "passages": session.scalar(select(func.count()).select_from(KbChunk)),
        },
        "activity": [{"day": d, "uploads": uploads.get(d, 0), "explanations": explanations.get(d, 0),
                      "questions": questions.get(d, 0)} for d in days],
    }


@router.get("/jobs", response_model=list[JobOut])
def jobs(state: str | None = None, session: Session = Depends(get_session),  # noqa: B008
         user: AppUser = Depends(staff)):  # noqa: B008
    q = select(ProcessingJob).order_by(ProcessingJob.id.desc()).limit(100)
    if state:
        try:
            q = q.where(ProcessingJob.status == JobStatus(state))
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unknown job state.") from exc
    return [JobOut(id=j.id, report_id=j.report_id, stage=j.stage.value, status=j.status.value, attempts=j.attempts,
                   error=j.error, created_at=j.created_at, finished_at=j.finished_at, locked_by=j.locked_by)
            for j in session.scalars(q)]


@router.post("/jobs/{job_id}/retry", response_model=JobOut)
def retry_job(job_id: int, session: Session = Depends(get_session), user: AppUser = Depends(admin)):  # noqa: B008
    job = session.get(ProcessingJob, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found.")
    if job.status is not JobStatus.FAILED:
        raise HTTPException(status.HTTP_409_CONFLICT, {"detail": "Only a failed job can be retried.",
                                                       "code": "not_failed"})
    job.status, job.error, job.attempts = JobStatus.QUEUED, None, 0
    job.run_after, job.finished_at, job.locked_at, job.locked_by = datetime.now(UTC), None, None, None
    if (report := session.get(Report, job.report_id)) and job.stage in RETRY_STATUS:
        report.status = RETRY_STATUS[job.stage]
    audit.record(session, user.id, "admin.job_retry", "job", None, job=job.id, stage=job.stage.value)
    session.commit()
    return JobOut(id=job.id, report_id=job.report_id, stage=job.stage.value, status=job.status.value,
                  attempts=job.attempts, error=job.error, created_at=job.created_at, finished_at=job.finished_at,
                  locked_by=job.locked_by)


@router.get("/audit", response_model=list[AuditOut])
def audit_log(action: str | None = None, before: int | None = None, session: Session = Depends(get_session),  # noqa: B008
              user: AppUser = Depends(staff)):  # noqa: B008
    q = (select(AuditLog, AppUser.email).outerjoin(AppUser, AppUser.id == AuditLog.actor_user_id)
         .order_by(AuditLog.id.desc()).limit(100))
    if action:
        q = q.where(AuditLog.action.startswith(action))
    if before:
        q = q.where(AuditLog.id < before)
    return [AuditOut(id=a.id, at=a.at, actor=email, action=a.action, entity_type=a.entity_type, entity_id=a.entity_id,
                     meta=a.meta) for a, email in session.execute(q)]


# --- Users: admins only -------------------------------------------------------------------------------------------

def _user_out(session: Session, u: AppUser) -> AdminUserOut:
    now = datetime.now(UTC)
    return AdminUserOut(
        id=u.id, email=u.email, role=u.role, verified=u.email_verified_at is not None,
        totp=u.totp_enabled_at is not None, locked=bool(u.locked_until and u.locked_until > now),
        created_at=u.created_at, last_login_at=u.last_login_at,
        sessions=session.scalar(select(func.count()).where(UserSession.user_id == u.id,
                                                           UserSession.revoked_at.is_(None))) or 0,
        profiles=session.scalar(select(func.count()).where(Profile.owner_user_id == u.id,
                                                           Profile.deleted_at.is_(None))) or 0,
    )


def _target(session: Session, user_id: uuid.UUID) -> AppUser:
    u = session.get(AppUser, user_id)
    if u is None or u.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found.")
    return u


@router.get("/users", response_model=list[AdminUserOut])
def users(q: str | None = None, session: Session = Depends(get_session),  # noqa: B008
          user: AppUser = Depends(admin)):  # noqa: B008
    staff_first = case((AppUser.role == UserRole.USER, 1), else_=0)
    query = select(AppUser).where(AppUser.deleted_at.is_(None)).order_by(staff_first, AppUser.created_at).limit(200)
    if q:
        query = query.where(AppUser.email.contains(q.strip().lower()))
    return [_user_out(session, u) for u in session.scalars(query)]


@router.patch("/users/{user_id}", response_model=AdminUserOut)
def set_role(user_id: uuid.UUID, body: RoleIn, session: Session = Depends(get_session),  # noqa: B008
             user: AppUser = Depends(admin)):  # noqa: B008
    """Change a role. A new staff member must set up two-step sign-in before anything else (FR-41)."""
    target = _target(session, user_id)
    if target.id == user.id:
        raise HTTPException(status.HTTP_409_CONFLICT, {"detail": "You can't change your own role.", "code": "own_role"})
    before = target.role
    target.role = body.role
    audit.record(session, user.id, "admin.role", "user", target.id, before=before.value, after=body.role.value)
    session.commit()
    return _user_out(session, target)


@router.post("/users/{user_id}/unlock", response_model=AdminUserOut)
def unlock(user_id: uuid.UUID, session: Session = Depends(get_session), user: AppUser = Depends(admin)):  # noqa: B008
    target = _target(session, user_id)
    target.locked_until, target.failed_logins = None, 0
    audit.record(session, user.id, "admin.unlock", "user", target.id)
    session.commit()
    return _user_out(session, target)


@router.post("/users/{user_id}/sign-out", response_model=AdminUserOut)
def sign_out(user_id: uuid.UUID, session: Session = Depends(get_session), user: AppUser = Depends(admin)):  # noqa: B008
    target = _target(session, user_id)
    n = revoke_all(session, target.id)
    audit.record(session, user.id, "admin.sign_out", "user", target.id, sessions=n)
    session.commit()
    return _user_out(session, target)
