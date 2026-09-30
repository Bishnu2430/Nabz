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
from app.services.ingest import EXTENSIONS, has_consent, sniff_mime
from app.storage import StorageBackend

router = APIRouter(tags=["records"])
MAX_BYTES = 20 * 1024 * 1024


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
    return session.scalars(select(HealthRecord).where(HealthRecord.profile_id == profile_id).order_by(*order)).all()


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
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Consent is needed before records can be stored.")
    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The file is larger than 20 MB.")
    mime = sniff_mime(data)
    if mime is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Upload a PDF, JPG, PNG or WebP file.")
    record = HealthRecord(profile_id=profile.id, uploaded_by=user.id, kind=kind, title=title.strip(),
                          record_date=record_date, facility=(facility or "").strip() or None,
                          notes=(notes or "").strip() or None, mime_type=mime, size_bytes=len(data),
                          sha256=hashlib.sha256(data).hexdigest(), storage_key="")
    session.add(record)
    session.flush()
    record.storage_key = f"records/{record.id}/{uuid.uuid4().hex}{EXTENSIONS[mime]}"
    storage.put(record.storage_key, data)
    audit.record(session, user.id, "record.add", "health_record", record.id, kind=kind.value, bytes=len(data))
    session.commit()
    return record


@router.get("/v1/records/{record_id}/file")
def record_file(record_id: uuid.UUID, session: Session = Depends(get_session),  # noqa: B008
                user: AppUser = Depends(current_user), storage: StorageBackend = Depends(get_storage)):  # noqa: B008
    record = owned_record(session, user, record_id)
    return Response(storage.get(record.storage_key), media_type=record.mime_type,
                    headers={"Cache-Control": "private, no-store", "Content-Disposition": "inline",
                             "X-Content-Type-Options": "nosniff"})


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
    return record


@router.delete("/v1/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(record_id: uuid.UUID, session: Session = Depends(get_session),  # noqa: B008
                  user: AppUser = Depends(current_user), storage: StorageBackend = Depends(get_storage)):  # noqa: B008
    record = owned_record(session, user, record_id)
    key = record.storage_key
    audit.record(session, user.id, "record.delete", "health_record", record.id)
    session.delete(record)
    session.commit()
    storage.delete(key)
