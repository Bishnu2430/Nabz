"""Pipeline stage handlers. Each is idempotent per report: re-running replaces its output."""

from __future__ import annotations

from typing import Protocol

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.catalogue.data import CatalogueData
from app.extraction import extract
from app.extraction.interpret import Interpreter, RawRow
from app.extraction.ocr import OCREngine
from app.models import Observation, Profile, Report, ReportFile, ReportPage
from app.models.enums import JobStage, ObsStatus, ReportStatus
from app.services.analysis import analyse_profile
from app.services.interpretation import age_on, apply, build_interpreter, lab_test_ids
from app.storage import StorageBackend
from app.worker import queue
from app.worker.queue import Job


class StageHandler(Protocol):
    stage: JobStage

    def handle(self, job: Job, session: Session) -> None: ...


class ExtractionStage:
    """File → pages (text layer or OCR) → rows mapped to the catalogue, converted to canonical units and
    scored for confidence. The report then waits for human review."""

    stage = JobStage.EXTRACT

    def __init__(self, storage: StorageBackend, catalogue: CatalogueData, ocr: OCREngine | None = None,
                 interpreter: Interpreter | None = None):
        self.storage = storage
        self.catalogue = catalogue
        self.ocr = ocr
        self.interpreter = interpreter or build_interpreter(catalogue)

    def handle(self, job: Job, session: Session) -> None:
        report = session.get(Report, job.report_id)
        if report is None or report.deleted_at is not None:
            return  # deleted while queued: nothing to do
        files = session.scalars(select(ReportFile).where(ReportFile.report_id == report.id)
                                .order_by(ReportFile.created_at)).all()
        profile = session.get(Profile, report.profile_id)
        sex = profile.sex.value if profile else None
        ids = lab_test_ids(session)

        session.execute(delete(Observation).where(Observation.report_id == report.id))
        for f in files:
            session.execute(delete(ReportPage).where(ReportPage.report_file_id == f.id))

        for f in files:
            result = extract(self.storage.get(f.storage_key), f.mime_type, self.catalogue, ocr=self.ocr)
            if report.lab_name is None and result.lab_name:
                report.lab_name = result.lab_name[:200]
            if report.collected_at is None and result.collected_at:
                report.collected_at = result.collected_at
            age = age_on(profile, report.collected_at) if profile else None  # picks the catalogue range
            page_ids = {}
            for page in result.pages:
                rp = ReportPage(
                    report_file_id=f.id, page_no=page.number, width=round(page.width), height=round(page.height),
                    ocr={"source": page.source, "quality": page.quality, "skew": round(page.skew, 3),
                         "tokens": [[t.text, round(t.x0, 1), round(t.top, 1), round(t.x1, 1), round(t.bottom, 1),
                                     round(t.conf, 3)] for t in page.tokens]},
                )
                session.add(rp)
                session.flush()
                page_ids[page.number] = rp.id
            ocr_quality = [p.quality for p in result.pages if p.quality is not None]
            f.quality_score = min(ocr_quality) if ocr_quality else 1.0
            sources = {p.number: p.source for p in result.pages}
            for row in result.rows:
                obs = Observation(
                    report_id=report.id, report_page_id=page_ids.get(row.page), raw_name=row.raw_name,
                    raw_value=row.raw_value, raw_unit=row.raw_unit, raw_range=row.raw_range, raw_flag=row.flag,
                    section=row.section, status=ObsStatus.UNKNOWN, ocr_confidence=round(row.confidence, 4),
                    bbox={"page": row.page, "x0": round(row.bbox[0], 1), "top": round(row.bbox[1], 1),
                          "x1": round(row.bbox[2], 1), "bottom": round(row.bbox[3], 1)},
                )
                raw = RawRow(row.raw_name, row.raw_value, row.raw_unit, row.raw_range, row.flag, row.section,
                             row.confidence, sources.get(row.page, "ocr"))
                apply(obs, self.interpreter.interpret(raw, sex, age), ids)
                session.add(obs)
        report.status = ReportStatus.NEEDS_REVIEW


class AnalysisStage:
    """Confirmed values → status, critical limits, change since last time, trend and percentile (FR-16 – FR-20).

    The report's tests are recomputed across the person's whole history, so a report confirmed out of date
    order corrects the later reports' analysis too. The explanation stage (Sprint 5) is queued next.
    """

    stage = JobStage.ANALYSE

    def handle(self, job: Job, session: Session) -> None:
        report = session.get(Report, job.report_id)
        if report is None or report.deleted_at is not None:
            return
        test_ids = set(session.scalars(select(Observation.test_id).where(
            Observation.report_id == report.id, Observation.test_id.is_not(None))))
        analyse_profile(session, report.profile_id, test_ids)
        report.status = ReportStatus.EXPLAINING
        queue.enqueue(session, report.id, JobStage.EXPLAIN)
