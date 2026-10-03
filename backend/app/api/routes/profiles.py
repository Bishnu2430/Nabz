import uuid
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_session, get_storage, owned_profile
from app.models import AppUser, Consent, Explanation, LabTest, Observation, Profile, Reminder, Report, TrendInsight
from app.models.enums import ConsentPurpose, JobStage, ObsStatus, Relationship, ReportStatus
from app.schemas import ConsentIn, ConsentOut, ProfileIn, ProfileOut, ProfilePatch
from app.services import audit, data_rights
from app.services.analysis import analyse_profile, result_date
from app.services.briefs import brief, worst_first
from app.services.interpretation import age_on, current_interpreter, raw_row_of
from app.storage import StorageBackend
from app.worker import queue

router = APIRouter(prefix="/v1/profiles", tags=["profiles"])
POLICY_VERSION = "2026-09-draft"
ADULT = 18
CONFIRMED = (ReportStatus.VERIFIED, ReportStatus.ANALYSING, ReportStatus.EXPLAINING, ReportStatus.EXPLAINED)


def _minor(dob: date | None) -> bool:
    if dob is None:
        return False
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day)) < ADULT


def _check_guardian(dob: date | None, relationship: Relationship, confirmed: bool) -> None:
    """FR-05 and the DPDP Act's rule for children: consent for someone under 18 comes from a parent or lawful
    guardian, so the account holder must say they are one; and an account holder must themselves be an adult."""
    if not _minor(dob):
        return
    if relationship is Relationship.SELF:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, {
            "detail": "You must be 18 or older to use Nabz yourself. A parent or guardian can add you to their family.",
            "code": "self_minor"})
    if not confirmed:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, {
            "detail": "For someone under 18, confirm that you are their parent or lawful guardian.",
            "code": "guardian_required"})


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
    upcoming: dict = {}
    for r in session.scalars(select(Reminder).where(Reminder.profile_id.in_(ids), Reminder.done_at.is_(None))
                             .order_by(Reminder.due_on.desc())):
        upcoming[r.profile_id] = r  # ordered latest first, so the soonest is what remains
    return [ProfileOut.model_validate(p).model_copy(update={
        "reports": n or 0, "latest_report_at": latest, "last_tested": last_tested.get(p.id),
        "attention": worst_first(attention.get(p.id, [])),
        "next_reminder_title": upcoming[p.id].title if p.id in upcoming else None,
        "next_reminder_due": upcoming[p.id].due_on if p.id in upcoming else None,
    }) for p, n, latest in rows]


@router.post("", response_model=ProfileOut, status_code=status.HTTP_201_CREATED)
def create_profile(body: ProfileIn, session: Session = Depends(get_session),  # noqa: B008
                   user: AppUser = Depends(current_user)):  # noqa: B008
    _check_guardian(body.date_of_birth, body.relationship, body.guardian_confirmed)
    profile = Profile(owner_user_id=user.id, **body.model_dump(exclude={"consent_processing", "guardian_confirmed"}))
    if _minor(body.date_of_birth):
        profile.guardian_confirmed_at = datetime.now(UTC)
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
    profile = owned_profile(session, user, profile_id)
    if body.granted and _minor(profile.date_of_birth) and profile.guardian_confirmed_at is None:
        raise HTTPException(status.HTTP_409_CONFLICT, {
            "detail": "For someone under 18, confirm that you are their parent or lawful guardian first.",
            "code": "guardian_required"})
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


@router.patch("/{profile_id}", response_model=ProfileOut)
def edit_profile(profile_id: uuid.UUID, body: ProfilePatch, session: Session = Depends(get_session),  # noqa: B008
                 user: AppUser = Depends(current_user)):  # noqa: B008
    """Correct a person's details (FR-02). Sex and date of birth choose the typical ranges used where a report
    printed none, and the population a result is compared with, so changing them re-reads those ranges, analyses
    again, and rewrites the explanation of any report whose results changed status."""
    profile = owned_profile(session, user, profile_id)
    changes = body.model_dump(exclude_unset=True, exclude={"guardian_confirmed"})
    dob = changes.get("date_of_birth", profile.date_of_birth)
    relationship = changes.get("relationship", profile.relationship)
    _check_guardian(dob, relationship, bool(body.guardian_confirmed) or profile.guardian_confirmed_at is not None)
    if _minor(dob) and profile.guardian_confirmed_at is None:
        profile.guardian_confirmed_at = datetime.now(UTC)
    ranges_change = (("sex" in changes and changes["sex"] != profile.sex)
                     or ("date_of_birth" in changes and changes["date_of_birth"] != profile.date_of_birth))
    for field, value in changes.items():
        if value is not None or field == "date_of_birth":
            setattr(profile, field, value)
    if ranges_change:
        _reread_ranges(session, profile)
    audit.record(session, user.id, "profile.edit", "profile", profile.id, fields=sorted(changes))
    session.commit()
    return ProfileOut.model_validate(profile)


def _reread_ranges(session: Session, profile: Profile) -> None:
    rows = session.execute(
        select(Observation, Report, LabTest).join(Report, Report.id == Observation.report_id)
        .join(LabTest, LabTest.id == Observation.test_id)
        .where(Report.profile_id == profile.id, Report.deleted_at.is_(None), Report.status.in_(CONFIRMED))).all()
    before = {o.id: o.status for o, _, _ in rows}
    interp = current_interpreter(session)
    for obs, report, test in rows:
        if obs.ref_source != "catalogue":
            continue  # the lab's own printed range doesn't depend on who the person is
        it = interp.interpret(raw_row_of(obs, "manual"), profile.sex.value, age_on(profile, report.collected_at),
                              test_code=test.code)
        obs.ref_low, obs.ref_high = it.ref_low, it.ref_high
    session.flush()
    analyse_profile(session, profile.id)
    changed = {r.id for o, r, _ in rows if o.status != before[o.id]}
    for report_id in changed:
        languages = set(session.scalars(select(Explanation.language).where(Explanation.report_id == report_id)))
        session.execute(delete(Explanation).where(Explanation.report_id == report_id))
        for language in languages or {profile.preferred_language}:
            queue.enqueue(session, report_id, JobStage.EXPLAIN, args={"lang": language.value})


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
