"""Accept an uploaded report file and queue it for extraction (FR-04, FR-06)."""

from __future__ import annotations

import hashlib
import uuid

import pypdfium2 as pdfium
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Consent, Report, ReportFile
from app.models.enums import ConsentPurpose, JobStage, ReportStatus
from app.storage import StorageBackend
from app.worker import queue

MAX_BYTES = 10 * 1024 * 1024
MAX_PAGES = 10
EXTENSIONS = {"application/pdf": ".pdf", "image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


class IngestError(ValueError):
    """The upload was refused; the message is safe to show to the user. `code` and `params` let the app say it in
    the reader's language."""

    def __init__(self, message: str, code: str = "refused", **params: object):
        super().__init__(message)
        self.code = code
        self.params = params


class DuplicateReport(IngestError):
    def __init__(self, report_id: uuid.UUID):
        super().__init__("This report has already been uploaded for this person.", "duplicate")
        self.report_id = report_id


def sniff_mime(data: bytes) -> str | None:
    """Detect the file type from its first bytes; the file name and client-sent type are not trusted."""
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def has_consent(session: Session, profile_id: uuid.UUID, purpose: ConsentPurpose) -> bool:
    return session.scalar(
        select(Consent.id).where(Consent.profile_id == profile_id, Consent.purpose == purpose,
                                 Consent.revoked_at.is_(None)).limit(1)
    ) is not None


def ingest_report(session: Session, storage: StorageBackend, *, profile_id: uuid.UUID, uploaded_by: uuid.UUID,
                  data: bytes) -> Report:
    if not has_consent(session, profile_id, ConsentPurpose.PROCESSING):
        raise IngestError("Processing consent is needed before a report can be read.", "no_consent")
    if len(data) > MAX_BYTES:
        raise IngestError("The file is larger than 10 MB.", "too_large", limit=10)
    mime = sniff_mime(data)
    if mime is None:
        raise IngestError("Upload a PDF, JPG, PNG or WebP file.", "file_type")
    if mime == "application/pdf":
        try:
            pdf = pdfium.PdfDocument(data)
            pages = len(pdf)
            pdf.close()
        except pdfium.PdfiumError as exc:
            raise IngestError("The PDF could not be opened.", "bad_pdf") from exc
        if pages > MAX_PAGES:
            raise IngestError(f"The PDF has {pages} pages; the limit is {MAX_PAGES}.", "too_many_pages", pages=pages,
                              limit=MAX_PAGES)

    digest = hashlib.sha256(data).hexdigest()
    existing = session.scalar(select(Report.id).where(Report.profile_id == profile_id, Report.source_sha256 == digest,
                                                      Report.deleted_at.is_(None)))
    if existing:
        raise DuplicateReport(existing)

    report = Report(profile_id=profile_id, uploaded_by=uploaded_by, source_sha256=digest, status=ReportStatus.QUEUED)
    session.add(report)
    session.flush()
    key = f"reports/{report.id}/{uuid.uuid4().hex}{EXTENSIONS[mime]}"
    storage.put(key, data)
    session.add(ReportFile(report_id=report.id, storage_key=key, mime_type=mime, size_bytes=len(data), sha256=digest))
    queue.enqueue(session, report.id, JobStage.EXTRACT)
    return report
