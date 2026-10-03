"""Data rights (docs/10 §3): export everything held about a person (FR-32) and erase it (FR-33).

Everything includes the other health records (imaging reports, prescriptions) and the person's own notes.

Erasure is a hard delete. Rows go through the foreign-key cascades (report → files, pages, observations,
explanations; profile → reports, consents, trend insights), and the stored objects are listed first so they can be
removed once the transaction has committed. Only a minimal audit entry, with no health data, remains.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import ColumnElement, select, union
from sqlalchemy.orm import Session

from app.models import (
    Clinician,
    ClinicianNote,
    Consent,
    Explanation,
    HealthRecord,
    HomeReading,
    LabTest,
    Observation,
    OrganSystem,
    Profile,
    Reminder,
    Report,
    ReportFile,
    ReportGrant,
    ReportQuestion,
)
from app.storage import StorageBackend

EXPORT_FORMAT = "nabz-export"
EXPORT_VERSION = 1


def stored_keys(session: Session, reports: ColumnElement[bool]) -> list[str]:
    """Every stored object behind the reports matching `reports`: the uploads and the narration audio."""
    files = select(ReportFile.storage_key.label("key")).join(Report, Report.id == ReportFile.report_id).where(reports)
    audio = (select(Explanation.audio_key.label("key")).join(Report, Report.id == Explanation.report_id)
             .where(reports, Explanation.audio_key.is_not(None)))
    return list(session.scalars(select(union(files, audio).subquery().c.key)))


def record_keys(session: Session, records: ColumnElement[bool]) -> list[str]:
    """The stored files of the other health records matching `records`, with the study images taken from them."""
    keys: set[str] = set()
    for file_key, image_key in session.execute(select(HealthRecord.storage_key, HealthRecord.image_key).where(records)):
        keys.update(k for k in (file_key, image_key) if k)
    return sorted(keys)


def remove_objects(storage: StorageBackend, keys: list[str]) -> None:
    """After the commit: a failure here leaves an orphaned object, never a row pointing at a missing file."""
    for key in keys:
        storage.delete(key)


def _num(v: Any) -> str | None:
    return None if v is None else str(v)


def _iso(v: Any) -> str | None:
    return None if v is None else v.isoformat()


def export_profile(session: Session, profile: Profile) -> dict[str, Any]:
    """A self-describing JSON document with the person, consents, reports, results as printed and as confirmed,
    the analysis, and every explanation. Stored files are listed with their checksums, not embedded."""
    consents = session.scalars(select(Consent).where(Consent.profile_id == profile.id)
                               .order_by(Consent.granted_at)).all()
    reports = session.scalars(select(Report).where(Report.profile_id == profile.id, Report.deleted_at.is_(None))
                              .order_by(Report.collected_at.asc().nulls_last(), Report.created_at)).all()
    out_reports = []
    for r in reports:
        files = session.scalars(select(ReportFile).where(ReportFile.report_id == r.id)).all()
        rows = session.execute(
            select(Observation, LabTest.code, LabTest.canonical_name, OrganSystem.code)
            .outerjoin(LabTest, LabTest.id == Observation.test_id)
            .outerjoin(OrganSystem, OrganSystem.id == LabTest.organ_system_id)
            .where(Observation.report_id == r.id).order_by(Observation.created_at)).all()
        explanations = session.scalars(select(Explanation).where(Explanation.report_id == r.id)
                                       .order_by(Explanation.created_at)).all()
        out_reports.append({
            "id": str(r.id),
            "lab_name": r.lab_name,
            "collected_at": _iso(r.collected_at),
            "uploaded_at": _iso(r.created_at),
            "status": r.status.value,
            "your_note": r.note,
            "files": [{"mime_type": f.mime_type, "size_bytes": f.size_bytes, "sha256": f.sha256} for f in files],
            "results": [{
                "test_code": code,
                "test_name": name,
                "organ_system": organ,
                "as_printed": {"name": o.raw_name, "value": o.raw_value, "unit": o.raw_unit, "range": o.raw_range,
                               "flag": o.raw_flag},
                "value": _num(o.value_num),
                "unit": o.unit,
                "ref_low": _num(o.ref_low),
                "ref_high": _num(o.ref_high),
                "ref_source": o.ref_source,
                "status": o.status.value,
                "edited_by_you": o.edited,
                "confirmed_at": _iso(o.verified_at),
                "analysis": o.analysis,
            } for o, code, name, organ in rows],
            "explanations": [{
                "language": e.language.value,
                "written_by": e.model_id,
                "prompt_version": e.prompt_version,
                "safety_status": e.safety_status.value,
                "created_at": _iso(e.created_at),
                "content": e.content,
            } for e in explanations],
            "shared_with_doctors": [{
                "doctor": name, "registration": reg, "shared_at": _iso(g.created_at),
                "withdrawn_at": _iso(g.revoked_at),
            } for g, name, reg in session.execute(
                select(ReportGrant, Clinician.full_name, Clinician.registration_no)
                .join(Clinician, Clinician.user_id == ReportGrant.clinician_user_id)
                .where(ReportGrant.report_id == r.id).order_by(ReportGrant.created_at))],
            "doctors_notes": [{"doctor": name, "written_at": _iso(n.created_at), "note": n.text}
                              for n, name in session.execute(
                                  select(ClinicianNote, Clinician.full_name)
                                  .outerjoin(Clinician, Clinician.user_id == ClinicianNote.clinician_user_id)
                                  .where(ClinicianNote.report_id == r.id).order_by(ClinicianNote.created_at))],
            "questions": [{
                "asked_at": _iso(q.created_at), "language": q.language.value, "question": q.question,
                "answer": q.answer, "answered_by": q.mode,
            } for q in session.scalars(select(ReportQuestion).where(ReportQuestion.report_id == r.id)
                                       .order_by(ReportQuestion.created_at))],
        })
    records = session.scalars(select(HealthRecord).where(HealthRecord.profile_id == profile.id)
                              .order_by(HealthRecord.record_date.asc().nulls_last(), HealthRecord.created_at)).all()
    return {
        "format": EXPORT_FORMAT,
        "version": EXPORT_VERSION,
        "exported_at": datetime.now(UTC).isoformat(),
        "notice": "Nabz explains results. It does not diagnose. Talk to your doctor about your results.",
        "person": {
            "display_name": profile.display_name,
            "sex": profile.sex.value,
            "date_of_birth": _iso(profile.date_of_birth),
            "relationship": profile.relationship.value,
            "preferred_language": profile.preferred_language.value,
            "guardian_confirmed_at": _iso(profile.guardian_confirmed_at),
            "added_at": _iso(profile.created_at),
        },
        "consents": [{"purpose": c.purpose.value, "policy_version": c.policy_version,
                      "granted_at": _iso(c.granted_at), "withdrawn_at": _iso(c.revoked_at)} for c in consents],
        "reports": out_reports,
        "other_records": [{
            "kind": r.kind.value, "title": r.title, "date": _iso(r.record_date), "facility": r.facility,
            "notes": r.notes, "file": {"mime_type": r.mime_type, "size_bytes": r.size_bytes, "sha256": r.sha256},
            "report_text": r.study,
        } for r in records],
        "emergency_card": profile.emergency,
        "reminders": [{
            "title": r.title, "test_code": r.test_code, "due_on": _iso(r.due_on), "repeat_months": r.repeat_months,
            "note": r.note, "done_at": _iso(r.done_at),
        } for r in session.scalars(select(Reminder).where(Reminder.profile_id == profile.id)
                                   .order_by(Reminder.due_on))],
        "home_readings": {
            "targets": profile.reading_targets,
            "readings": [{
                "kind": r.kind.value, "value": _num(r.value), "value2": _num(r.value2), "context": r.context,
                "note": r.note, "taken_at": _iso(r.taken_at),
            } for r in session.scalars(select(HomeReading).where(HomeReading.profile_id == profile.id)
                                       .order_by(HomeReading.taken_at))],
        },
    }


def export_filename(profile: Profile) -> str:
    slug = "".join(ch if ch.isascii() and ch.isalnum() else "-" for ch in profile.display_name.lower()).strip("-")
    return f"nabz-{slug or 'person'}-{datetime.now(UTC):%Y-%m-%d}.json"


def profile_reports(profile_id: uuid.UUID) -> ColumnElement[bool]:
    return Report.profile_id == profile_id


def profile_records(profile_id: uuid.UUID) -> ColumnElement[bool]:
    return HealthRecord.profile_id == profile_id


def account_reports(user_id: uuid.UUID) -> ColumnElement[bool]:
    return Report.profile_id.in_(select(Profile.id).where(Profile.owner_user_id == user_id))


def account_records(user_id: uuid.UUID) -> ColumnElement[bool]:
    return HealthRecord.profile_id.in_(select(Profile.id).where(Profile.owner_user_id == user_id))
