"""Other health records: imaging reports, prescriptions, discharge summaries (stored and listed, not analysed)."""

from __future__ import annotations

import hashlib
import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_session, get_storage, owned_profile
from app.models import AppUser, HealthRecord
from app.models.enums import ConsentPurpose, RecordKind
from app.schemas import RecordOut, RecordPatch
from app.services import audit
from app.services.imaging import extract_study
from app.services.ingest import EXTENSIONS, has_consent, sniff_mime
from app.storage import StorageBackend

router = APIRouter(tags=["records"])
MAX_BYTES = 20 * 1024 * 1024


def record_out(r: HealthRecord) -> RecordOut:
    study = r.study or {}
    return RecordOut.model_validate(r).model_copy(update={
        "has_image": r.image_key is not None, "study_title": study.get("title"),
        "findings": study.get("findings", []), "impression": study.get("impression", []),
        "image_credit": study.get("credit"),
    })


def attach_study(record: HealthRecord, data: bytes, storage: StorageBackend) -> None:
    """For imaging, keep the study image and the report's title, findings and impression."""
    if record.kind is not RecordKind.IMAGING:
        return
    study = extract_study(data, record.mime_type)
    if study.image is None:
        return
    if record.mime_type.startswith("image/"):
        record.image_key = record.storage_key
    else:
        record.image_key = f"records/{record.id}/{uuid.uuid4().hex}.jpg"
        storage.put(record.image_key, study.image)
    record.study = {"title": study.title, "findings": study.findings, "impression": study.impression,
                    "credit": study.credit}


def owned_record(session: Session, user: AppUser, record_id: uuid.UUID) -> HealthRecord:
    record = session.get(HealthRecord, record_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Record not found.")
    owned_profile(session, user, record.profile_id)
    return record


@router.get("/v1/profiles/{profile_id}/records", response_model=list[RecordOut])
def list_records(profile_id: uuid.UUID, session: Session = Depends(get_session),  # noqa: B008
                 user: AppUser = Depends(current_user)):  # noqa: B008
    owned_profile(session, user, profile_id)
    order = (HealthRecord.record_date.desc().nulls_last(), HealthRecord.created_at.desc())
    rows = session.scalars(select(HealthRecord).where(HealthRecord.profile_id == profile_id).order_by(*order))
    return [record_out(r) for r in rows]


@router.post("/v1/profiles/{profile_id}/records", response_model=RecordOut, status_code=status.HTTP_201_CREATED)
async def add_record(profile_id: uuid.UUID, file: UploadFile = File(...),  # noqa: B008
                     kind: RecordKind = Form(...), title: str = Form(..., min_length=1, max_length=120),  # noqa: B008
                     record_date: date | None = Form(None), facility: str | None = Form(None, max_length=120),  # noqa: B008
                     notes: str | None = Form(None, max_length=1000),  # noqa: B008
                     session: Session = Depends(get_session), user: AppUser = Depends(current_user),  # noqa: B008
                     storage: StorageBackend = Depends(get_storage)):  # noqa: B008
    profile = owned_profile(session, user, profile_id)
    if user.email_verified_at is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            {"detail": "Confirm your email before uploading.", "code": "verify_email"})
    if not has_consent(session, profile.id, ConsentPurpose.PROCESSING):
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            {"detail": "Consent is needed before records can be stored.", "code": "no_consent"})
    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            {"detail": "The file is larger than 20 MB.", "code": "too_large", "limit": 20})
    mime = sniff_mime(data)
    if mime is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            {"detail": "Upload a PDF, JPG, PNG or WebP file.", "code": "file_type"})
    record = HealthRecord(profile_id=profile.id, uploaded_by=user.id, kind=kind, title=title.strip(),
                          record_date=record_date, facility=(facility or "").strip() or None,
                          notes=(notes or "").strip() or None, mime_type=mime, size_bytes=len(data),
                          sha256=hashlib.sha256(data).hexdigest(), storage_key="")
    session.add(record)
    session.flush()
    record.storage_key = f"records/{record.id}/{uuid.uuid4().hex}{EXTENSIONS[mime]}"
    storage.put(record.storage_key, data)
    attach_study(record, data, storage)
    audit.record(session, user.id, "record.add", "health_record", record.id, kind=kind.value, bytes=len(data))
    session.commit()
    return record_out(record)


@router.get("/v1/records/{record_id}/file")
def record_file(record_id: uuid.UUID, session: Session = Depends(get_session),  # noqa: B008
                user: AppUser = Depends(current_user), storage: StorageBackend = Depends(get_storage)):  # noqa: B008
    record = owned_record(session, user, record_id)
    return Response(storage.get(record.storage_key), media_type=record.mime_type,
                    headers={"Cache-Control": "private, no-store", "Content-Disposition": "inline",
                             "X-Content-Type-Options": "nosniff"})


@router.get("/v1/records/{record_id}/image")
def record_image(record_id: uuid.UUID, session: Session = Depends(get_session),  # noqa: B008
                 user: AppUser = Depends(current_user), storage: StorageBackend = Depends(get_storage)):  # noqa: B008
    """The study image on its own, for the viewer."""
    record = owned_record(session, user, record_id)
    if record.image_key is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This record has no image.")
    mime = record.mime_type if record.image_key == record.storage_key else "image/jpeg"
    return Response(storage.get(record.image_key), media_type=mime,
                    headers={"Cache-Control": "private, max-age=3600", "X-Content-Type-Options": "nosniff"})


@router.patch("/v1/records/{record_id}", response_model=RecordOut)
def edit_record(record_id: uuid.UUID, body: RecordPatch, session: Session = Depends(get_session),  # noqa: B008
                user: AppUser = Depends(current_user)):  # noqa: B008
    record = owned_record(session, user, record_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        if isinstance(value, str):
            value = value.strip() or None
        if field in ("title", "kind") and value is None:
            continue  # required: an empty value leaves them unchanged
        setattr(record, field, value)
    audit.record(session, user.id, "record.edit", "health_record", record.id)
    session.commit()
    return record_out(record)


@router.delete("/v1/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(record_id: uuid.UUID, session: Session = Depends(get_session),  # noqa: B008
                  user: AppUser = Depends(current_user), storage: StorageBackend = Depends(get_storage)):  # noqa: B008
    record = owned_record(session, user, record_id)
    keys = {record.storage_key, record.image_key} - {None}
    audit.record(session, user.id, "record.delete", "health_record", record.id)
    session.delete(record)
    session.commit()
    for key in keys:
        storage.delete(key)
