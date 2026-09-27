"""Ingest → worker → draft observations, against a real database and the committed samples."""

import json
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.catalogue import CatalogueData
from app.core.config import settings
from app.models import Observation, Report, ReportPage
from app.models.enums import JobStage, ReportStatus
from app.services.ingest import DuplicateReport, IngestError, ingest_report
from app.storage import LocalVolumeStorage
from app.worker import queue
from app.worker.runner import Worker
from app.worker.stages import ExtractionStage
from tests.factories import make_profile

pytestmark = pytest.mark.db
SAMPLES = Path(settings.data_dir) / "synthetic" / "samples"


@pytest.fixture
def storage(tmp_path: Path) -> LocalVolumeStorage:
    return LocalVolumeStorage(tmp_path / "uploads")


def _ingest(sessions: sessionmaker[Session], storage: LocalVolumeStorage, sample: str) -> Report:
    with sessions.begin() as s:
        profile = make_profile(s)
        return ingest_report(s, storage, profile_id=profile.id, uploaded_by=profile.owner_user_id,
                             data=(SAMPLES / f"{sample}.pdf").read_bytes())


def test_pdf_report_is_extracted_for_review(sessions: sessionmaker[Session], storage: LocalVolumeStorage,
                                            catalogue: CatalogueData) -> None:
    truth = json.loads((SAMPLES / "syn-2026-0001.json").read_text(encoding="utf-8"))
    report = _ingest(sessions, storage, "syn-2026-0001")
    worker = Worker(sessions, [ExtractionStage(storage, catalogue)])
    assert worker.run_once()
    with sessions() as s:
        r = s.get(Report, report.id)
        assert r.status == ReportStatus.NEEDS_REVIEW and r.lab_name.startswith("Mahanadi")
        rows = s.scalars(select(Observation).where(Observation.report_id == report.id)).all()
        assert len(rows) == len(truth["rows"])
        got = sorted(Decimal(o.raw_value.replace(",", "")) for o in rows)
        assert got == sorted(Decimal(g["printed_value"].replace(",", "")) for g in truth["rows"])
        assert {o.raw_flag for o in rows} >= {g["flag"] or None for g in truth["rows"]}
        assert all(o.bbox and o.report_page_id for o in rows)
        assert s.scalar(select(func.count()).select_from(ReportPage)) == truth["pages"]
    assert not worker.run_once()  # queue is empty


def test_reprocessing_replaces_previous_output(sessions: sessionmaker[Session], storage: LocalVolumeStorage,
                                               catalogue: CatalogueData) -> None:
    report = _ingest(sessions, storage, "syn-2026-0003")
    worker = Worker(sessions, [ExtractionStage(storage, catalogue)])
    worker.run_once()
    with sessions.begin() as s:
        queue.enqueue(s, report.id, JobStage.EXTRACT)
    worker.run_once()
    with sessions() as s:
        truth = json.loads((SAMPLES / "syn-2026-0003.json").read_text(encoding="utf-8"))
        n = s.scalar(select(func.count()).select_from(Observation).where(Observation.report_id == report.id))
        assert n == len(truth["rows"])


class _BrokenStorage(LocalVolumeStorage):
    def get(self, key: str) -> bytes:
        raise OSError("disk unavailable")


def test_repeated_failures_mark_the_report_failed(sessions: sessionmaker[Session], storage: LocalVolumeStorage,
                                                  catalogue: CatalogueData) -> None:
    report = _ingest(sessions, storage, "syn-2026-0004")
    worker = Worker(sessions, [ExtractionStage(_BrokenStorage(storage.root), catalogue)])
    for attempt in range(1, queue.MAX_ATTEMPTS + 1):
        with sessions.begin() as s:
            s.execute(text("UPDATE processing_job SET run_after = now()"))
        assert worker.run_once()
        with sessions() as s:
            expected = ReportStatus.QUEUED if attempt < queue.MAX_ATTEMPTS else ReportStatus.FAILED
            assert s.get(Report, report.id).status == expected


def test_ingest_rules(sessions: sessionmaker[Session], storage: LocalVolumeStorage) -> None:
    pdf = (SAMPLES / "syn-2026-0005.pdf").read_bytes()
    with sessions.begin() as s:
        no_consent = make_profile(s, consent=False, email="a@nabz.local")
        profile = make_profile(s, email="b@nabz.local")
        kwargs = {"uploaded_by": profile.owner_user_id}
        with pytest.raises(IngestError, match="consent"):
            ingest_report(s, storage, profile_id=no_consent.id, data=pdf, **kwargs)
        with pytest.raises(IngestError, match="PDF, JPG"):
            ingest_report(s, storage, profile_id=profile.id, data=b"GIF89a....", **kwargs)
        with pytest.raises(IngestError, match="10 MB"):
            ingest_report(s, storage, profile_id=profile.id, data=b"%PDF-" + b"0" * (10 * 1024 * 1024), **kwargs)
        first = ingest_report(s, storage, profile_id=profile.id, data=pdf, **kwargs)
        with pytest.raises(DuplicateReport) as dup:
            ingest_report(s, storage, profile_id=profile.id, data=pdf, **kwargs)
        assert dup.value.report_id == first.id
