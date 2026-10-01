"""Reminders the family set for themselves: the next one in a repeating series, the email, the calendar file."""

from __future__ import annotations

import calendar
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import AppUser, Profile, Reminder
from app.services import mail

TEXT = {
    "en": ("Nabz reminder: {title}",
           "A reminder you set in Nabz for {person}:\n\n{title}\nDue: {due}\n{note}\n"
           "Open {person}'s page:\n{link}\n\nYou set this date yourself; Nabz doesn't decide when a test is needed."),
    "hi": ("नब्ज़ रिमाइंडर: {title}",
           "{person} के लिए नब्ज़ में आपका रिमाइंडर:\n\n{title}\nतारीख: {due}\n{note}\n{person} का पेज खोलें:\n{link}\n\n"
           "यह तारीख आपने खुद तय की है; नब्ज़ यह तय नहीं करता कि जाँच कब ज़रूरी है।"),
}


def add_months(day: date, months: int) -> date:
    """The same day `months` later, or the month's last day when it has no such day (31 Jan + 1 month = 28 Feb)."""
    index = day.month - 1 + months
    year, month = day.year + index // 12, index % 12 + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def complete(session: Session, reminder: Reminder) -> Reminder | None:
    """Mark done; a repeating reminder leaves its next occurrence behind."""
    reminder.done_at = datetime.now(UTC)
    if not reminder.repeat_months:
        return None
    following = Reminder(profile_id=reminder.profile_id, created_by=reminder.created_by, title=reminder.title,
                         test_code=reminder.test_code, due_on=add_months(reminder.due_on, reminder.repeat_months),
                         repeat_months=reminder.repeat_months, note=reminder.note)
    session.add(following)
    return following


def send_email(session: Session, reminder: Reminder) -> bool:
    """Email the account holder. Returns False when there is no one to send to."""
    profile = session.get(Profile, reminder.profile_id)
    user = session.get(AppUser, profile.owner_user_id) if profile else None
    if user is None or user.deleted_at is not None:
        return False
    subject, body = TEXT.get(user.preferred_language.value) or TEXT["en"]
    fields = {"title": reminder.title, "person": profile.display_name, "due": reminder.due_on.strftime("%d %b %Y"),
              "note": f"Note: {reminder.note}\n" if reminder.note else "",
              "link": f"{settings.app_base_url}/p/{profile.id}"}
    mail.send(user.email, subject.format(**fields), body.format(**fields))
    reminder.sent_at = datetime.now(UTC)
    return True


def send_due(session: Session, today: date | None = None) -> int:
    """Email every reminder that has come due and hasn't been sent. Called by the worker once a minute."""
    today = today or datetime.now(UTC).date()
    due = session.scalars(select(Reminder).where(Reminder.due_on <= today, Reminder.sent_at.is_(None),
                                                 Reminder.done_at.is_(None))).all()
    return sum(send_email(session, r) for r in due)


def ics(reminder: Reminder, person: str) -> str:
    """One all-day calendar event, repeating if the reminder does (RFC 5545)."""
    def esc(text: str) -> str:
        return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Nabz//Reminders//EN", "BEGIN:VEVENT",
        f"UID:{reminder.id}@nabz", f"DTSTAMP:{datetime.now(UTC):%Y%m%dT%H%M%SZ}",
        f"DTSTART;VALUE=DATE:{reminder.due_on:%Y%m%d}", f"SUMMARY:{esc(f'{reminder.title} ({person})')}",
    ]
    if reminder.note:
        lines.append(f"DESCRIPTION:{esc(reminder.note)}")
    if reminder.repeat_months:
        lines.append(f"RRULE:FREQ=MONTHLY;INTERVAL={reminder.repeat_months}")
    lines += ["END:VEVENT", "END:VCALENDAR"]
    return "\r\n".join(lines) + "\r\n"
