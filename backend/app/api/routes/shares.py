"""Share a report with a doctor (FR-34): an expiring, revocable, read-only link that needs no account.

The link carries a random token; only its SHA-256 is stored, so the link can be shown once and never recovered
from the database. Opening it shows one report: the person's name, age and sex, the confirmed results with their
analysis, the family's note and the questions prepared for the doctor. Nothing can be changed through it.
"""

from __future__ import annotations

import base64
import io
import uuid
from datetime import timedelta

import segno
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_session, owned_report
from app.api.routes.insights import report_view
from app.core import security
from app.core.config import settings
from app.models import AppUser, Explanation, Profile, Report, ShareLink
from app.schemas import ShareCreated, SharedPerson, SharedReportOut, ShareIn, ShareOut
from app.services import audit
from app.services.analysis import result_date
from app.services.auth import RateLimiter, now
from app.services.interpretation import age_on

router = APIRouter(tags=["sharing"])
view_limiter = RateLimiter(60, 60)  # per IP address: plenty for a doctor, little for guessing tokens
GONE = "This link has expired or was withdrawn. Ask the person who shared it for a new one."


def _out(link: ShareLink) -> ShareOut:
    live = link.revoked_at is None and link.expires_at > now()
    return ShareOut(id=link.id, label=link.label, created_at=link.created_at, expires_at=link.expires_at,
                    revoked=link.revoked_at is not None, active=live, views=link.views,
                    last_viewed_at=link.last_viewed_at)


@router.post("/v1/reports/{report_id}/shares", response_model=ShareCreated, status_code=status.HTTP_201_CREATED)
def create_share(report_id: uuid.UUID, body: ShareIn, session: Session = Depends(get_session),  # noqa: B008
                 user: AppUser = Depends(current_user)):  # noqa: B008
    report = owned_report(session, user, report_id)
    token = security.new_token()
    link = ShareLink(report_id=report.id, created_by=user.id, token_hash=security.token_hash(token),
                     label=(body.label or "").strip() or None, expires_at=now() + timedelta(days=body.days))
    session.add(link)
    audit.record(session, user.id, "share.create", "report", report.id, days=body.days)
    session.commit()
    url = f"{settings.app_base_url}/s/{token}"
    buf = io.BytesIO()
    segno.make(url, error="m").save(buf, kind="svg", scale=5, border=2, dark="#1f1d1b", light="#fbf8f2")
    qr = "data:image/svg+xml;base64," + base64.b64encode(buf.getvalue()).decode()
    return ShareCreated(**_out(link).model_dump(), url=url, qr_svg=qr)


@router.get("/v1/reports/{report_id}/shares", response_model=list[ShareOut])
def list_shares(report_id: uuid.UUID, session: Session = Depends(get_session),  # noqa: B008
                user: AppUser = Depends(current_user)):  # noqa: B008
    report = owned_report(session, user, report_id)
    links = session.scalars(select(ShareLink).where(ShareLink.report_id == report.id)
                            .order_by(ShareLink.created_at.desc())).all()
    return [_out(link) for link in links]


@router.delete("/v1/shares/{share_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_share(share_id: uuid.UUID, session: Session = Depends(get_session),  # noqa: B008
                 user: AppUser = Depends(current_user)):  # noqa: B008
    link = session.get(ShareLink, share_id)
    if link is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Link not found.")
    owned_report(session, user, link.report_id)
    if link.revoked_at is None:
        link.revoked_at = now()
        audit.record(session, user.id, "share.revoke", "report", link.report_id)
    session.commit()


@router.get("/v1/shared/{token}", response_model=SharedReportOut)
def shared_report(token: str, request: Request, session: Session = Depends(get_session)):  # noqa: B008
    """No session: the token is the key. Every answer for a bad, expired or withdrawn token is the same 404."""
    if not view_limiter.allow(request.client.host if request.client else "unknown"):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many requests. Wait a minute and try again.")
    link = session.scalar(select(ShareLink).where(ShareLink.token_hash == security.token_hash(token)))
    if link is None or link.revoked_at is not None or link.expires_at <= now():
        raise HTTPException(status.HTTP_404_NOT_FOUND, GONE)
    report = session.get(Report, link.report_id)
    if report is None or report.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, GONE)
    link.views += 1
    link.last_viewed_at = now()
    audit.record(session, None, "share.view", "report", report.id)
    view = shared_view(session, report)
    session.commit()
    return view.model_copy(update={"expires_at": link.expires_at})


def shared_view(session: Session, report: Report) -> SharedReportOut:
    """One report as a doctor sees it, read-only: through a share link, or as a clinician it was shared with."""
    profile = session.get(Profile, report.profile_id)
    _, results, organs = report_view(session, report)

    # the questions prepared for the doctor, in the person's language where an explanation exists in it
    explanations = {e.language.value: e for e in session.scalars(
        select(Explanation).where(Explanation.report_id == report.id))}
    chosen = (explanations.get(profile.preferred_language.value) or explanations.get("en")
              or next(iter(explanations.values()), None))
    questions = list((chosen.content if chosen else {}).get("doctor_questions") or [])
    return SharedReportOut(
        person=SharedPerson(display_name=profile.display_name, sex=profile.sex,
                            age=age_on(profile, result_date(report))),
        lab_name=report.lab_name, collected_at=report.collected_at, note=report.note,
        critical=[r for r in results if r.critical], organs=organs, questions=questions,
    )
