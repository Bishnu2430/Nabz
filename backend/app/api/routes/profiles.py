from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_session
from app.models import AppUser, Consent, Profile, Report
from app.models.enums import ConsentPurpose
from app.schemas import ProfileIn, ProfileOut
from app.services import audit

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
    return [ProfileOut.model_validate(p).model_copy(update={"reports": n or 0, "latest_report_at": latest})
            for p, n, latest in rows]


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
