"""Doctors on Nabz (docs/12 §2): a clinician's registration and verification, the reports a family shares with a
verified clinician, and the notes the clinician leaves for the family.

A clinician sees only reports shared with them, read-only, for as long as the family keeps the share; every view
is audited. Sharing with an account that isn't a verified clinician answers the same way as sharing with no account,
so the endpoint doesn't reveal who has an account.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_session, owned_report, require_roles
from app.api.routes.shares import shared_view
from app.models import AppUser, Clinician, ClinicianNote, Profile, Report, ReportGrant
from app.models.enums import UserRole
from app.schemas import (
    AdminClinicianOut,
    ClinicianIn,
    ClinicianOut,
    GrantIn,
    GrantOut,
    NoteIn,
    NoteOut,
    SharedPerson,
    SharedReportOut,
    SharedWithMe,
    VerifyIn,
)
from app.services import audit
from app.services.analysis import result_date
from app.services.auth import normalise_email
from app.services.interpretation import age_on

router = APIRouter(tags=["clinicians"])
clinician = require_roles(UserRole.CLINICIAN)
admin = require_roles(UserRole.ADMIN)
NO_CLINICIAN = {"detail": "There is no verified doctor on Nabz with that email.", "code": "no_clinician"}


def _notes(session: Session, report_id: uuid.UUID) -> list[NoteOut]:
    rows = session.execute(select(ClinicianNote, Clinician.full_name)
                           .outerjoin(Clinician, Clinician.user_id == ClinicianNote.clinician_user_id)
                           .where(ClinicianNote.report_id == report_id).order_by(ClinicianNote.created_at)).all()
    return [NoteOut(id=n.id, text=n.text, created_at=n.created_at, clinician_name=name) for n, name in rows]


# --- The clinician's own side ---------------------------------------------------------------------------------------

@router.get("/v1/clinician/me", response_model=ClinicianOut | None)
def my_registration(session: Session = Depends(get_session), user: AppUser = Depends(clinician)):  # noqa: B008
    return session.get(Clinician, user.id)


@router.put("/v1/clinician/me", response_model=ClinicianOut)
def set_registration(body: ClinicianIn, session: Session = Depends(get_session),  # noqa: B008
                     user: AppUser = Depends(clinician)):  # noqa: B008
    """A changed registration has to be checked again before anything more is shared."""
    row = session.get(Clinician, user.id)
    fields = {k: (v.strip() if isinstance(v, str) else v) or None for k, v in body.model_dump().items()}
    if row is None:
        row = Clinician(user_id=user.id, **fields)
        session.add(row)
    else:
        if (fields["registration_no"], fields["council"]) != (row.registration_no, row.council):
            row.verified_at, row.verified_by = None, None
        for k, v in fields.items():
            setattr(row, k, v)
    audit.record(session, user.id, "clinician.registration", "user", user.id)
    session.commit()
    return row


def _granted(session: Session, user: AppUser, report_id: uuid.UUID) -> Report:
    registration = session.get(Clinician, user.id)
    grant = session.scalar(select(ReportGrant).where(ReportGrant.report_id == report_id,
                                                     ReportGrant.clinician_user_id == user.id,
                                                     ReportGrant.revoked_at.is_(None)))
    report = session.get(Report, report_id)
    if registration is None or registration.verified_at is None or grant is None or report is None \
            or report.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found.")
    return report


@router.get("/v1/clinician/shared", response_model=list[SharedWithMe])
def shared_with_me(session: Session = Depends(get_session), user: AppUser = Depends(clinician)):  # noqa: B008
    registration = session.get(Clinician, user.id)
    if registration is None or registration.verified_at is None:
        return []
    counts = (select(ClinicianNote.report_id, func.count().label("n")).group_by(ClinicianNote.report_id).subquery())
    rows = session.execute(
        select(ReportGrant, Report, Profile, counts.c.n).join(Report, Report.id == ReportGrant.report_id)
        .join(Profile, Profile.id == Report.profile_id).outerjoin(counts, counts.c.report_id == Report.id)
        .where(ReportGrant.clinician_user_id == user.id, ReportGrant.revoked_at.is_(None),
               Report.deleted_at.is_(None)).order_by(ReportGrant.created_at.desc())).all()
    return [SharedWithMe(report_id=r.id, person=SharedPerson(display_name=p.display_name, sex=p.sex,
                                                             age=age_on(p, result_date(r))),
                         lab_name=r.lab_name, collected_at=r.collected_at, shared_at=g.created_at, notes=n or 0)
            for g, r, p, n in rows]


@router.get("/v1/clinician/reports/{report_id}", response_model=SharedReportOut)
def clinician_report(report_id: uuid.UUID, session: Session = Depends(get_session),  # noqa: B008
                     user: AppUser = Depends(clinician)):  # noqa: B008
    report = _granted(session, user, report_id)
    view = shared_view(session, report)
    audit.record(session, user.id, "clinician.view", "report", report.id)
    session.commit()
    return view.model_copy(update={"notes": _notes(session, report.id)})


@router.post("/v1/clinician/reports/{report_id}/notes", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
def add_note(report_id: uuid.UUID, body: NoteIn, session: Session = Depends(get_session),  # noqa: B008
             user: AppUser = Depends(clinician)):  # noqa: B008
    report = _granted(session, user, report_id)
    note = ClinicianNote(report_id=report.id, clinician_user_id=user.id, text=body.text.strip())
    session.add(note)
    session.flush()
    audit.record(session, user.id, "clinician.note", "report", report.id)
    session.commit()
    return NoteOut(id=note.id, text=note.text, created_at=note.created_at,
                   clinician_name=session.get(Clinician, user.id).full_name)


# --- The family's side ------------------------------------------------------------------------------------------------

def _grant_out(session: Session, g: ReportGrant, c: Clinician) -> GrantOut:
    notes = session.scalar(select(func.count()).where(ClinicianNote.report_id == g.report_id,
                                                      ClinicianNote.clinician_user_id == g.clinician_user_id)) or 0
    return GrantOut(id=g.id, clinician_name=c.full_name, registration_no=c.registration_no, council=c.council,
                    specialty=c.specialty, created_at=g.created_at, revoked=g.revoked_at is not None, notes=notes)


@router.post("/v1/reports/{report_id}/grants", response_model=GrantOut, status_code=status.HTTP_201_CREATED)
def share_with_clinician(report_id: uuid.UUID, body: GrantIn, session: Session = Depends(get_session),  # noqa: B008
                         user: AppUser = Depends(current_user)):  # noqa: B008
    report = owned_report(session, user, report_id)
    found = session.execute(select(AppUser, Clinician).join(Clinician, Clinician.user_id == AppUser.id).where(
        AppUser.email == normalise_email(body.email), AppUser.role == UserRole.CLINICIAN,
        AppUser.deleted_at.is_(None), Clinician.verified_at.is_not(None))).first()
    if found is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_CLINICIAN)
    doctor, registration = found
    grant = session.scalar(select(ReportGrant).where(ReportGrant.report_id == report.id,
                                                     ReportGrant.clinician_user_id == doctor.id,
                                                     ReportGrant.revoked_at.is_(None)))
    if grant is None:
        grant = ReportGrant(report_id=report.id, clinician_user_id=doctor.id, granted_by=user.id)
        session.add(grant)
        session.flush()
        audit.record(session, user.id, "grant.create", "report", report.id, clinician=str(doctor.id))
        session.commit()
    return _grant_out(session, grant, registration)


@router.get("/v1/reports/{report_id}/grants", response_model=list[GrantOut])
def list_grants(report_id: uuid.UUID, session: Session = Depends(get_session),  # noqa: B008
                user: AppUser = Depends(current_user)):  # noqa: B008
    report = owned_report(session, user, report_id)
    rows = session.execute(
        select(ReportGrant, Clinician).join(Clinician, Clinician.user_id == ReportGrant.clinician_user_id)
        .where(ReportGrant.report_id == report.id).order_by(ReportGrant.created_at.desc())).all()
    return [_grant_out(session, g, c) for g, c in rows]


@router.delete("/v1/grants/{grant_id}", status_code=status.HTTP_204_NO_CONTENT)
def withdraw_grant(grant_id: uuid.UUID, session: Session = Depends(get_session),  # noqa: B008
                   user: AppUser = Depends(current_user)):  # noqa: B008
    grant = session.get(ReportGrant, grant_id)
    if grant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found.")
    owned_report(session, user, grant.report_id)
    if grant.revoked_at is None:
        grant.revoked_at = datetime.now(UTC)
        audit.record(session, user.id, "grant.revoke", "report", grant.report_id)
    session.commit()


@router.get("/v1/reports/{report_id}/notes", response_model=list[NoteOut])
def report_notes(report_id: uuid.UUID, session: Session = Depends(get_session),  # noqa: B008
                 user: AppUser = Depends(current_user)):  # noqa: B008
    return _notes(session, owned_report(session, user, report_id).id)


# --- Verification: admins ---------------------------------------------------------------------------------------------

@router.get("/v1/admin/clinicians", response_model=list[AdminClinicianOut])
def list_clinicians(session: Session = Depends(get_session), user: AppUser = Depends(admin)):  # noqa: B008
    rows = session.execute(select(Clinician, AppUser.email).join(AppUser, AppUser.id == Clinician.user_id)
                           .where(AppUser.deleted_at.is_(None)).order_by(Clinician.verified_at.is_not(None),
                                                                         Clinician.created_at)).all()
    return [AdminClinicianOut(**ClinicianOut.model_validate(c).model_dump(), user_id=c.user_id, email=email)
            for c, email in rows]


@router.post("/v1/admin/clinicians/{user_id}/verify", response_model=AdminClinicianOut)
def verify_clinician(user_id: uuid.UUID, body: VerifyIn, session: Session = Depends(get_session),  # noqa: B008
                     user: AppUser = Depends(admin)):  # noqa: B008
    """The admin has checked the registration against the council's register (docs/12 §2)."""
    row = session.get(Clinician, user_id)
    account = session.get(AppUser, user_id)
    if row is None or account is None or account.role is not UserRole.CLINICIAN:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Clinician not found.")
    row.verified_at, row.verified_by = (datetime.now(UTC), user.id) if body.verified else (None, None)
    audit.record(session, user.id, "admin.clinician_verify", "user", user_id, verified=body.verified)
    session.commit()
    return AdminClinicianOut(**ClinicianOut.model_validate(row).model_dump(), user_id=row.user_id, email=account.email)
