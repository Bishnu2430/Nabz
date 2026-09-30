import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_session, get_storage, owned_profile
from app.models import AppUser, Consent, LabTest, Observation, Profile, Report, TrendInsight
from app.models.enums import ConsentPurpose, ObsStatus, ReportStatus
from app.schemas import ConsentIn, ConsentOut, ProfileIn, ProfileOut
from app.services import audit, data_rights
from app.services.analysis import result_date
from app.services.briefs import brief, worst_first
from app.storage import StorageBackend

router = APIRouter(prefix="/v1/profiles", tags=["profiles"])
POLICY_VERSION = "2026-09-draft"


@router.get("", response_model=list[ProfileOut])
def list_profiles(session: Session = Depends(get_session), user: AppUser = Depends(current_user)):  # noqa: B008
    stats = (select(Report.profile_id, func.count().label("n"), func.max(Report.created_at).label("latest"))
             .where(Report.deleted_at.is_(None)).group_by(Report.profile_id).subquery())
    rows = session.execute(
        select(Profile, stats.c.n, stats.c.latest).outerjoin(stats, stats.c.profile_id == Profile.id)
        .where(Profile.owner_user_id == user.id, Profile.deleted_at.is_(None)).order_by(Profile.created_at)
    ).all()
    ids = [p.id for p, _, _ in rows]
    confirmed = (ReportStatus.VERIFIED, ReportStatus.ANALYSING, ReportStatus.EXPLAINING, ReportStatus.EXPLAINED)
    last_tested: dict = {}
    for r in session.scalars(select(Report).where(Report.profile_id.in_(ids), Report.deleted_at.is_(None),
                                                  Report.status.in_(confirmed))):
        last_tested[r.profile_id] = max(last_tested.get(r.profile_id, result_date(r)), result_date(r))
    attention: dict = {}
    for t, obs, test, report in session.execute(
        select(TrendInsight, Observation, LabTest, Report)
        .join(Observation, Observation.id == TrendInsight.last_observation_id)
        .join(LabTest, LabTest.id == Observation.test_id).join(Report, Report.id == Observation.report_id)
        .where(TrendInsight.profile_id.in_(ids), Observation.status.notin_([ObsStatus.NORMAL, ObsStatus.UNKNOWN]))
    ):
        attention.setdefault(t.profile_id, []).append(brief(obs, test, report))
    return [ProfileOut.model_validate(p).model_copy(update={
        "reports": n or 0, "latest_report_at": latest, "last_tested": last_tested.get(p.id),
        "attention": worst_first(attention.get(p.id, [])),
    }) for p, n, latest in rows]


@router.post("", response_model=ProfileOut, status_code=status.HTTP_201_CREATED)
def create_profile(body: ProfileIn, session: Session = Depends(get_session),  # noqa: B008
                   user: AppUser = Depends(current_user)):  # noqa: B008
    profile = Profile(owner_user_id=user.id, **body.model_dump(exclude={"consent_processing"}))
    session.add(profile)
    session.flush()
    if body.consent_processing:
        session.add(Consent(user_id=user.id, profile_id=profile.id, purpose=ConsentPurpose.PROCESSING,
                            policy_version=POLICY_VERSION))
    audit.record(session, user.id, "profile.create", "profile", profile.id, consent_processing=body.consent_processing)
    session.commit()
    return ProfileOut.model_validate(profile)


def _active(session: Session, profile_id: uuid.UUID, purpose: ConsentPurpose) -> Consent | None:
    return session.scalar(select(Consent).where(Consent.profile_id == profile_id, Consent.purpose == purpose,
                                                Consent.revoked_at.is_(None)).order_by(Consent.granted_at.desc()))


@router.get("/{profile_id}/consents", response_model=list[ConsentOut])
def list_consents(profile_id: uuid.UUID, session: Session = Depends(get_session),  # noqa: B008
                  user: AppUser = Depends(current_user)):  # noqa: B008
    """Current state of every purpose (FR-03): processing, external AI, voice, research."""
    owned_profile(session, user, profile_id)
    out = []
    for purpose in ConsentPurpose:
        c = _active(session, profile_id, purpose)
        out.append(ConsentOut(purpose=purpose, granted=c is not None, granted_at=c.granted_at if c else None))
    return out


@router.put("/{profile_id}/consents/{purpose}", response_model=ConsentOut)
def set_consent(profile_id: uuid.UUID, purpose: ConsentPurpose, body: ConsentIn,
                session: Session = Depends(get_session), user: AppUser = Depends(current_user)):  # noqa: B008
    """Give or withdraw one consent. Withdrawing is as easy as giving (DPDP); records are kept as evidence."""
    owned_profile(session, user, profile_id)
    if purpose is ConsentPurpose.PROCESSING and not body.granted:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Processing consent is withdrawn by deleting this person's reports or profile.")
    current = _active(session, profile_id, purpose)
    if body.granted and current is None:
        current = Consent(user_id=user.id, profile_id=profile_id, purpose=purpose, policy_version=POLICY_VERSION)
        session.add(current)
    elif not body.granted and current is not None:
        current.revoked_at = datetime.now(UTC)
        current = None
    audit.record(session, user.id, "consent.set", "profile", profile_id, purpose=purpose.value, granted=body.granted)
    session.commit()
    return ConsentOut(purpose=purpose, granted=current is not None, granted_at=current.granted_at if current else None)


@router.get("/{profile_id}/export")
def export_profile(profile_id: uuid.UUID, session: Session = Depends(get_session),  # noqa: B008
                   user: AppUser = Depends(current_user)):  # noqa: B008
    """Everything Nabz holds about this person, as one JSON file (FR-32)."""
    profile = owned_profile(session, user, profile_id)
    body = data_rights.export_profile(session, profile)
    audit.record(session, user.id, "profile.export", "profile", profile.id, reports=len(body["reports"]))
    session.commit()
    return JSONResponse(body, headers={
        "Content-Disposition": f'attachment; filename="{data_rights.export_filename(profile)}"',
        "Cache-Control": "no-store",
    })


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(profile_id: uuid.UUID, session: Session = Depends(get_session),  # noqa: B008
                   user: AppUser = Depends(current_user),  # noqa: B008
                   storage: StorageBackend = Depends(get_storage)):  # noqa: B008
    """Hard delete (FR-33): the person, their reports, files, audio, results, explanations and consents."""
    profile = owned_profile(session, user, profile_id)
    keys = (data_rights.stored_keys(session, data_rights.profile_reports(profile.id))
            + data_rights.record_keys(session, data_rights.profile_records(profile.id)))
    audit.record(session, user.id, "profile.delete", "profile", profile.id, files=len(keys))
    session.execute(delete(Profile).where(Profile.id == profile.id))
    session.commit()
    data_rights.remove_objects(storage, keys)
