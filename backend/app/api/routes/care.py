"""What a family keeps beside the lab reports: reminders they set, readings they take at home, and the details
for an emergency card. None of it is interpreted: reminders use the family's own dates, readings are compared only
with the target the person entered, and the card prints what was typed."""

from __future__ import annotations

import base64
import io
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import segno
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_session, owned_profile
from app.models import AppUser, HomeReading, LabTest, Observation, Profile, Reminder, Report, TrendInsight
from app.models.enums import ObsStatus, ReadingKind, ReportStatus
from app.schemas import (
    EmergencyCardOut,
    EmergencyInfo,
    PersonOut,
    ReadingIn,
    ReadingOut,
    ReadingTarget,
    ReminderIn,
    ReminderOut,
    ReminderPatch,
)
from app.services import audit, reminders
from app.services.analysis import result_date
from app.services.briefs import brief, worst_first
from app.services.interpretation import age_on

router = APIRouter(tags=["care"])

# What a home device can plausibly show; outside this the entry is a typing mistake.
PLAUSIBLE: dict[ReadingKind, tuple[Decimal, Decimal]] = {
    ReadingKind.BP: (Decimal(60), Decimal(260)),
    ReadingKind.GLUCOSE: (Decimal(20), Decimal(700)),
    ReadingKind.WEIGHT: (Decimal(2), Decimal(300)),
    ReadingKind.PULSE: (Decimal(25), Decimal(230)),
    ReadingKind.TEMPERATURE: (Decimal(30), Decimal(44)),
    ReadingKind.SPO2: (Decimal(50), Decimal(100)),
}
DIASTOLIC = (Decimal(30), Decimal(160))


# --- Reminders -------------------------------------------------------------------------------------------------------

def _reminder(session: Session, user: AppUser, reminder_id: uuid.UUID) -> Reminder:
    reminder = session.get(Reminder, reminder_id)
    if reminder is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reminder not found.")
    owned_profile(session, user, reminder.profile_id)
    return reminder


@router.get("/v1/profiles/{profile_id}/reminders", response_model=list[ReminderOut])
def list_reminders(profile_id: uuid.UUID, session: Session = Depends(get_session),  # noqa: B008
                   user: AppUser = Depends(current_user)):  # noqa: B008
    owned_profile(session, user, profile_id)
    return session.scalars(select(Reminder).where(Reminder.profile_id == profile_id)
                           .order_by(Reminder.done_at.is_not(None), Reminder.due_on)).all()


@router.post("/v1/profiles/{profile_id}/reminders", response_model=ReminderOut, status_code=status.HTTP_201_CREATED)
def add_reminder(profile_id: uuid.UUID, body: ReminderIn, session: Session = Depends(get_session),  # noqa: B008
                 user: AppUser = Depends(current_user)):  # noqa: B008
    profile = owned_profile(session, user, profile_id)
    if body.test_code and session.scalar(select(LabTest.id).where(LabTest.code == body.test_code)) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unknown test.")
    reminder = Reminder(profile_id=profile.id, created_by=user.id, title=body.title.strip(), due_on=body.due_on,
                        test_code=body.test_code, repeat_months=body.repeat_months,
                        note=(body.note or "").strip() or None)
    session.add(reminder)
    session.flush()
    audit.record(session, user.id, "reminder.add", "reminder", reminder.id)
    session.commit()
    return reminder


@router.patch("/v1/reminders/{reminder_id}", response_model=ReminderOut)
def edit_reminder(reminder_id: uuid.UUID, body: ReminderPatch, session: Session = Depends(get_session),  # noqa: B008
                  user: AppUser = Depends(current_user)):  # noqa: B008
    """Change a reminder, or mark it done. A repeating reminder that is done leaves its next occurrence."""
    reminder = _reminder(session, user, reminder_id)
    changes = body.model_dump(exclude_unset=True)
    done = changes.pop("done", None)
    for field, value in changes.items():
        if isinstance(value, str):
            value = value.strip() or None
        if field in ("title", "due_on") and value is None:
            continue  # required: an empty value leaves them as they are
        setattr(reminder, field, value)
    if "due_on" in changes:
        reminder.sent_at = None  # a new date deserves its own email
    if done is True and reminder.done_at is None:
        reminders.complete(session, reminder)
    elif done is False:
        reminder.done_at = None
    session.commit()
    return reminder


@router.delete("/v1/reminders/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reminder(reminder_id: uuid.UUID, session: Session = Depends(get_session),  # noqa: B008
                    user: AppUser = Depends(current_user)):  # noqa: B008
    session.delete(_reminder(session, user, reminder_id))
    session.commit()


@router.post("/v1/reminders/{reminder_id}/send", response_model=ReminderOut)
def send_reminder_now(reminder_id: uuid.UUID, session: Session = Depends(get_session),  # noqa: B008
                      user: AppUser = Depends(current_user)):  # noqa: B008
    """Send the reminder email now rather than on its date (to try it out)."""
    reminder = _reminder(session, user, reminder_id)
    reminders.send_email(session, reminder)
    session.commit()
    return reminder


@router.get("/v1/reminders/{reminder_id}/calendar.ics")
def reminder_calendar(reminder_id: uuid.UUID, session: Session = Depends(get_session),  # noqa: B008
                      user: AppUser = Depends(current_user)):  # noqa: B008
    reminder = _reminder(session, user, reminder_id)
    person = session.get(Profile, reminder.profile_id).display_name
    return Response(reminders.ics(reminder, person), media_type="text/calendar",
                    headers={"Content-Disposition": 'attachment; filename="nabz-reminder.ics"',
                             "Cache-Control": "no-store"})


# --- Home readings ---------------------------------------------------------------------------------------------------

@router.get("/v1/profiles/{profile_id}/readings", response_model=list[ReadingOut])
def list_readings(profile_id: uuid.UUID, kind: ReadingKind | None = None,
                  session: Session = Depends(get_session), user: AppUser = Depends(current_user)):  # noqa: B008
    owned_profile(session, user, profile_id)
    q = select(HomeReading).where(HomeReading.profile_id == profile_id)
    if kind is not None:
        q = q.where(HomeReading.kind == kind)
    return session.scalars(q.order_by(HomeReading.taken_at.desc()).limit(1000)).all()


@router.post("/v1/profiles/{profile_id}/readings", response_model=ReadingOut, status_code=status.HTTP_201_CREATED)
def add_reading(profile_id: uuid.UUID, body: ReadingIn, session: Session = Depends(get_session),  # noqa: B008
                user: AppUser = Depends(current_user)):  # noqa: B008
    profile = owned_profile(session, user, profile_id)
    low, high = PLAUSIBLE[body.kind]
    if not low <= body.value <= high:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, {
            "detail": f"That doesn't look right. Enter a value between {low} and {high}.", "code": "implausible",
            "low": str(low), "high": str(high)})
    if body.kind is ReadingKind.BP:
        if body.value2 is None or not DIASTOLIC[0] <= body.value2 <= DIASTOLIC[1] or body.value2 >= body.value:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, {
                "detail": "Enter both numbers, the larger one first (for example 128 over 82).", "code": "bp_pair"})
    taken = body.taken_at or datetime.now(UTC)
    if taken.tzinfo is None:
        taken = taken.replace(tzinfo=UTC)
    if taken > datetime.now(UTC) + timedelta(minutes=5):  # a little slack for a phone's clock
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            {"detail": "The time can't be in the future.", "code": "future_time"})
    reading = HomeReading(profile_id=profile.id, kind=body.kind, value=body.value,
                          value2=body.value2 if body.kind is ReadingKind.BP else None,
                          context=(body.context or "").strip() or None, note=(body.note or "").strip() or None,
                          taken_at=taken)
    session.add(reading)
    session.commit()
    return reading


@router.delete("/v1/readings/{reading_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reading(reading_id: uuid.UUID, session: Session = Depends(get_session),  # noqa: B008
                   user: AppUser = Depends(current_user)):  # noqa: B008
    reading = session.get(HomeReading, reading_id)
    if reading is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reading not found.")
    owned_profile(session, user, reading.profile_id)
    session.delete(reading)
    session.commit()


@router.get("/v1/profiles/{profile_id}/reading-targets", response_model=dict[str, ReadingTarget])
def reading_targets(profile_id: uuid.UUID, session: Session = Depends(get_session),  # noqa: B008
                    user: AppUser = Depends(current_user)):  # noqa: B008
    return owned_profile(session, user, profile_id).reading_targets or {}


@router.put("/v1/profiles/{profile_id}/reading-targets/{kind}", response_model=dict[str, ReadingTarget])
def set_reading_target(profile_id: uuid.UUID, kind: ReadingKind, body: ReadingTarget,
                       session: Session = Depends(get_session), user: AppUser = Depends(current_user)):  # noqa: B008
    """The range the person's doctor gave them; an empty target removes it."""
    profile = owned_profile(session, user, profile_id)
    targets = dict(profile.reading_targets or {})
    target = {k: str(v) for k, v in body.model_dump().items() if v is not None}
    if target:
        targets[kind.value] = target
    else:
        targets.pop(kind.value, None)
    profile.reading_targets = targets
    session.commit()
    return targets


# --- Emergency card --------------------------------------------------------------------------------------------------

def _card_text(profile: Profile, info: EmergencyInfo, age: int | None) -> str:
    """What the QR code holds: plain text any phone camera can show with no network."""
    who = ", ".join(x for x in (profile.display_name, f"{age} y" if age is not None else "",
                                profile.sex.value if profile.sex.value in ("female", "male") else "") if x)
    lines = ["EMERGENCY CARD", who]
    for label, value in (("Blood group", info.blood_group), ("Allergies", info.allergies),
                         ("Conditions", info.conditions), ("Medicines", info.medicines), ("Doctor", info.doctor)):
        if value:
            lines.append(f"{label}: {value}")
    for c in info.contacts:
        lines.append(f"Call: {c.name}{f' ({c.relation})' if c.relation else ''} {c.phone}")
    return "\n".join(lines)


@router.get("/v1/profiles/{profile_id}/emergency", response_model=EmergencyCardOut)
def emergency_card(profile_id: uuid.UUID, session: Session = Depends(get_session),  # noqa: B008
                   user: AppUser = Depends(current_user)):  # noqa: B008
    profile = owned_profile(session, user, profile_id)
    info = EmergencyInfo.model_validate(profile.emergency or {})
    age = age_on(profile, None)
    out = [brief(obs, test, report) for _, obs, test, report in session.execute(
        select(TrendInsight, Observation, LabTest, Report)
        .join(Observation, Observation.id == TrendInsight.last_observation_id)
        .join(LabTest, LabTest.id == Observation.test_id).join(Report, Report.id == Observation.report_id)
        .where(TrendInsight.profile_id == profile.id,
               Observation.status.notin_([ObsStatus.NORMAL, ObsStatus.UNKNOWN])))]
    confirmed = (ReportStatus.VERIFIED, ReportStatus.ANALYSING, ReportStatus.EXPLAINING, ReportStatus.EXPLAINED)
    dates = [result_date(r) for r in session.scalars(select(Report).where(
        Report.profile_id == profile.id, Report.deleted_at.is_(None), Report.status.in_(confirmed)))]
    text = _card_text(profile, info, age)
    buf = io.BytesIO()
    segno.make(text, error="m").save(buf, kind="svg", scale=4, border=2, dark="#1f1d1b", light="#ffffff")
    return EmergencyCardOut(
        person=PersonOut(id=profile.id, display_name=profile.display_name, sex=profile.sex, age=age), info=info,
        out_of_range=worst_first(out), last_tested=max(dates) if dates else None, qr_text=text,
        qr_svg="data:image/svg+xml;base64," + base64.b64encode(buf.getvalue()).decode(),
    )


@router.put("/v1/profiles/{profile_id}/emergency", response_model=EmergencyInfo)
def set_emergency(profile_id: uuid.UUID, body: EmergencyInfo, session: Session = Depends(get_session),  # noqa: B008
                  user: AppUser = Depends(current_user)):  # noqa: B008
    profile = owned_profile(session, user, profile_id)
    cleaned = {k: (v.strip() or None) if isinstance(v, str) else v for k, v in body.model_dump().items()}
    profile.emergency = cleaned
    audit.record(session, user.id, "profile.emergency", "profile", profile.id)
    session.commit()
    return EmergencyInfo.model_validate(cleaned)
