from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import current_user, get_session, get_sessionmaker, get_storage, owned_profile, owned_report
from app.extraction.interpret import Interpreter
from app.models import AppUser, LabTest, Observation, Profile, Report, ReportFile, ReportPage
from app.models.enums import JobStage, ObsStatus, ReportStatus
from app.schemas import (
    Accepted,
    Box,
    ConfirmIn,
    ObservationNew,
    ObservationOut,
    ObservationPatch,
    PageOut,
    ReportNoteIn,
    ReportOut,
    ReportSummary,
)
from app.services import audit, data_rights
from app.services.analysis import analyse_profile
from app.services.briefs import brief, worst_first
from app.services.ingest import DuplicateReport, IngestError, ingest_report
from app.services.interpretation import age_on, apply, default_interpreter, lab_test_ids, raw_row_of
from app.services.pages import render_page
from app.storage import StorageBackend
from app.worker import queue

router = APIRouter(tags=["reports"])
EDITABLE = {ReportStatus.NEEDS_REVIEW}
FINAL = {ReportStatus.NEEDS_REVIEW, ReportStatus.VERIFIED, ReportStatus.EXPLAINED, ReportStatus.FAILED,
         ReportStatus.REJECTED}


def get_interpreter() -> Interpreter:
    return default_interpreter()


def _blocks_confirm(o: Observation) -> bool:
    """A row can't be confirmed until it has a test and a number (the same rule as confirm_report)."""
    return o.test_id is None or o.value_num is None


def _obs_out(o: Observation, tests: dict[int, LabTest], names: dict[str, str], threshold: float) -> ObservationOut:
    test = tests.get(o.test_id) if o.test_id else None
    return ObservationOut(
        id=o.id, raw_name=o.raw_name, raw_value=o.raw_value, raw_unit=o.raw_unit, raw_range=o.raw_range,
        raw_flag=o.raw_flag, section=o.section, test_code=test.code if test else None,
        test_name=test.canonical_name if test else None, value=o.value_num, unit=o.unit, ref_low=o.ref_low,
        ref_high=o.ref_high, ref_source=o.ref_source, confidence=o.confidence,
        needs_attention=_blocks_confirm(o) or o.confidence < threshold, match_method=o.match_method,
        candidates=[(c, names.get(c, c), s) for c, s in (o.match_candidates or [])],
        bbox=Box(**o.bbox) if o.bbox else None, edited=o.edited,
    )


def _report_out(session: Session, report: Report, interp: Interpreter) -> ReportOut:
    tests = {t.id: t for t in session.scalars(select(LabTest))}
    names = {t.code: t.canonical_name for t in tests.values()}
    threshold = interp.model.threshold
    rows = session.scalars(select(Observation).where(Observation.report_id == report.id)).all()
    rows = sorted(rows, key=lambda o: (o.bbox or {}).get("page", 99) * 10_000 + (o.bbox or {}).get("top", 9_999))
    pages = session.execute(
        select(ReportPage).join(ReportFile, ReportFile.id == ReportPage.report_file_id)
        .where(ReportFile.report_id == report.id).order_by(ReportPage.page_no)
    ).scalars().all()
    obs = [_obs_out(o, tests, names, threshold) for o in rows]
    return ReportOut(
        id=report.id, profile_id=report.profile_id, status=report.status, lab_name=report.lab_name,
        collected_at=report.collected_at, created_at=report.created_at,
        pages=[PageOut(page_no=p.page_no, width=p.width, height=p.height, source=(p.ocr or {}).get("source", "ocr"),
                       quality=(p.ocr or {}).get("quality")) for p in pages],
        observations=obs, needs_attention=sum(o.needs_attention for o in obs),
        unmapped=sum(_blocks_confirm(o) for o in rows), confidence_threshold=threshold,
    )


@router.post("/v1/profiles/{profile_id}/reports", response_model=Accepted, status_code=status.HTTP_202_ACCEPTED)
async def upload_report(profile_id: uuid.UUID, file: UploadFile = File(...),  # noqa: B008
                        session: Session = Depends(get_session), user: AppUser = Depends(current_user),  # noqa: B008
                        storage: StorageBackend = Depends(get_storage)):  # noqa: B008
    profile = owned_profile(session, user, profile_id)
    if user.email_verified_at is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            {"detail": "Confirm your email before uploading a report.", "code": "verify_email"})
    data = await file.read()
    try:
        report = ingest_report(session, storage, profile_id=profile.id, uploaded_by=user.id, data=data)
    except DuplicateReport as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, {"detail": str(exc), "report_id": str(exc.report_id)}) from exc
    except IngestError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    audit.record(session, user.id, "report.upload", "report", report.id, bytes=len(data))
    session.commit()
    return Accepted(report_id=report.id, status=report.status)


@router.get("/v1/profiles/{profile_id}/reports", response_model=list[ReportSummary])
def list_reports(profile_id: uuid.UUID, session: Session = Depends(get_session),  # noqa: B008
                 user: AppUser = Depends(current_user)):  # noqa: B008
    owned_profile(session, user, profile_id)
    counts = select(Observation.report_id, func.count().label("n")).group_by(Observation.report_id).subquery()
    rows = session.execute(
        select(Report, counts.c.n).outerjoin(counts, counts.c.report_id == Report.id)
        .where(Report.profile_id == profile_id, Report.deleted_at.is_(None))
        .order_by(Report.collected_at.desc().nulls_last(), Report.created_at.desc())
    ).all()
    flagged: dict[uuid.UUID, list] = {}
    for obs, test, report in session.execute(
        select(Observation, LabTest, Report).join(LabTest, LabTest.id == Observation.test_id)
        .join(Report, Report.id == Observation.report_id)
        .where(Report.profile_id == profile_id, Report.deleted_at.is_(None), Observation.verified_at.is_not(None),
               Observation.value_num.is_not(None), Observation.status.notin_([ObsStatus.NORMAL, ObsStatus.UNKNOWN]))
    ):
        flagged.setdefault(report.id, []).append(brief(obs, test, report))
    return [ReportSummary(id=r.id, status=r.status, lab_name=r.lab_name, collected_at=r.collected_at,
                          created_at=r.created_at, rows=n or 0, note=r.note,
                          out_of_range=worst_first(flagged.get(r.id, []))) for r, n in rows]


@router.patch("/v1/reports/{report_id}", response_model=ReportSummary)
def set_report_note(report_id: uuid.UUID, body: ReportNoteIn, session: Session = Depends(get_session),  # noqa: B008
                    user: AppUser = Depends(current_user)):  # noqa: B008
    """The person's own note on a report ("not fasting", "started a new medicine"), shown with its results."""
    report = owned_report(session, user, report_id)
    report.note = (body.note or "").strip() or None
    audit.record(session, user.id, "report.note", "report", report.id)
    session.commit()
    n = session.scalar(select(func.count()).select_from(Observation).where(Observation.report_id == report.id))
    return ReportSummary(id=report.id, status=report.status, lab_name=report.lab_name,
                         collected_at=report.collected_at, created_at=report.created_at, rows=n or 0, note=report.note)


@router.get("/v1/reports/{report_id}", response_model=ReportOut)
def get_report(report_id: uuid.UUID, session: Session = Depends(get_session),  # noqa: B008
               user: AppUser = Depends(current_user), interp: Interpreter = Depends(get_interpreter)):  # noqa: B008
    return _report_out(session, owned_report(session, user, report_id), interp)


@router.get("/v1/reports/{report_id}/events")
async def report_events(report_id: uuid.UUID, request: Request, session: Session = Depends(get_session),  # noqa: B008
                        user: AppUser = Depends(current_user),  # noqa: B008
                        sessions: sessionmaker[Session] = Depends(get_sessionmaker)):  # noqa: B008
    """Server-Sent Events: one `status` event per change until the report stops processing."""
    owned_report(session, user, report_id)

    async def stream():
        last = None
        for _ in range(600):  # at most ten minutes
            if await request.is_disconnected():
                return
            with sessions() as s:
                r = s.get(Report, report_id)
                current = r.status if r else None
            if current != last:
                yield f"event: status\ndata: {json.dumps({'status': current.value if current else None})}\n\n"
                last = current
            if current is None or current in FINAL:
                return
            await asyncio.sleep(1)

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/v1/reports/{report_id}/pages/{page_no}/image")
def page_image(report_id: uuid.UUID, page_no: int, session: Session = Depends(get_session),  # noqa: B008
               user: AppUser = Depends(current_user), storage: StorageBackend = Depends(get_storage)):  # noqa: B008
    report = owned_report(session, user, report_id)
    row = session.execute(
        select(ReportFile, ReportPage).join(ReportPage, ReportPage.report_file_id == ReportFile.id)
        .where(ReportFile.report_id == report.id, ReportPage.page_no == page_no)
    ).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Page not found.")
    f, page = row
    meta = page.ocr or {}
    image, media_type = render_page(storage.get(f.storage_key), f.mime_type, page_no, meta.get("source", "ocr"),
                                    meta.get("skew"))
    return Response(image, media_type=media_type, headers={"Cache-Control": "private, max-age=3600"})


def _editable(session: Session, user: AppUser, report_id: uuid.UUID) -> Report:
    report = owned_report(session, user, report_id)
    if report.status not in EDITABLE:
        raise HTTPException(status.HTTP_409_CONFLICT, "This report can't be edited now.")
    return report


def _reinterpret(session: Session, obs: Observation, report: Report, interp: Interpreter,
                 test_code: str | None) -> None:
    profile = session.get(Profile, report.profile_id)
    it = interp.interpret(raw_row_of(obs, "manual"), profile.sex.value, age_on(profile, report.collected_at),
                          test_code=test_code)
    # The person has checked this row: trust it unless it is still inconsistent (unknown unit, implausible value).
    if it.test_code and it.unit_ok and it.plausible and it.features.get("flag_mismatch", 0) == 0:
        it.confidence = 1.0
    apply(obs, it, lab_test_ids(session))


@router.patch("/v1/observations/{observation_id}", response_model=ObservationOut)
def edit_observation(observation_id: uuid.UUID, body: ObservationPatch,
                     session: Session = Depends(get_session), user: AppUser = Depends(current_user),  # noqa: B008
                     interp: Interpreter = Depends(get_interpreter)):  # noqa: B008
    obs = session.get(Observation, observation_id)
    if obs is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Row not found.")
    report = _editable(session, user, obs.report_id)
    changes = body.model_dump(exclude_unset=True)
    code = changes.pop("test_code", None)
    if code is not None and interp.tests.get(code) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown test.")
    for k, v in changes.items():
        setattr(obs, k, v)
    if code is None and "raw_name" not in changes and obs.test_id is not None:
        code = session.get(LabTest, obs.test_id).code  # keep the current mapping; only the value or unit changed
    _reinterpret(session, obs, report, interp, code)  # None → match the (edited) name again
    obs.edited = True
    audit.record(session, user.id, "observation.edit", "observation", obs.id, fields=sorted(body.model_fields_set))
    session.commit()
    tests = {t.id: t for t in session.scalars(select(LabTest))}
    return _obs_out(obs, tests, {t.code: t.canonical_name for t in tests.values()}, interp.model.threshold)


@router.post("/v1/reports/{report_id}/observations", response_model=ObservationOut,
             status_code=status.HTTP_201_CREATED)
def add_observation(report_id: uuid.UUID, body: ObservationNew, session: Session = Depends(get_session),  # noqa: B008
                    user: AppUser = Depends(current_user), interp: Interpreter = Depends(get_interpreter)):  # noqa: B008
    report = _editable(session, user, report_id)
    test = interp.tests.get(body.test_code)
    if test is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown test.")
    obs = Observation(report_id=report.id, raw_name=test.name, raw_value=body.raw_value,
                      raw_unit=body.raw_unit or (test.unit if test.unit != "ratio" else None),
                      raw_range=body.raw_range, section=test.panel, edited=True)
    session.add(obs)
    _reinterpret(session, obs, report, interp, body.test_code)
    session.flush()
    audit.record(session, user.id, "observation.add", "observation", obs.id)
    session.commit()
    tests = {t.id: t for t in session.scalars(select(LabTest))}
    return _obs_out(obs, tests, {t.code: t.canonical_name for t in tests.values()}, interp.model.threshold)


@router.delete("/v1/observations/{observation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_observation(observation_id: uuid.UUID, session: Session = Depends(get_session),  # noqa: B008
                       user: AppUser = Depends(current_user)):  # noqa: B008
    obs = session.get(Observation, observation_id)
    if obs is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Row not found.")
    _editable(session, user, obs.report_id)
    audit.record(session, user.id, "observation.delete", "observation", obs.id)
    session.delete(obs)
    session.commit()


@router.post("/v1/reports/{report_id}/confirm", response_model=Accepted, status_code=status.HTTP_202_ACCEPTED)
def confirm_report(report_id: uuid.UUID, body: ConfirmIn, session: Session = Depends(get_session),  # noqa: B008
                   user: AppUser = Depends(current_user)):  # noqa: B008
    """The human-review gate (FR-15): nothing is analysed until every row is confirmed."""
    report = _editable(session, user, report_id)
    rows = session.scalars(select(Observation).where(Observation.report_id == report.id)).all()
    if not rows:
        raise HTTPException(status.HTTP_409_CONFLICT, "There are no values to confirm.")
    unmapped = [str(o.id) for o in rows if _blocks_confirm(o)]
    if unmapped:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            {"detail": "Choose a test for every row, or remove rows that aren't results.",
                             "observations": unmapped})
    now = datetime.now(UTC)
    for o in rows:
        o.verified_at = now
    if body.collected_at:
        report.collected_at = body.collected_at
    report.status = ReportStatus.VERIFIED
    queue.enqueue(session, report.id, JobStage.ANALYSE)
    audit.record(session, user.id, "report.confirm", "report", report.id, rows=len(rows))
    session.commit()
    return Accepted(report_id=report.id, status=report.status)


@router.delete("/v1/reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(report_id: uuid.UUID, session: Session = Depends(get_session),  # noqa: B008
                  user: AppUser = Depends(current_user), storage: StorageBackend = Depends(get_storage)):  # noqa: B008
    """Hard delete (FR-33): files and rows go; an audit entry remains."""
    report = owned_report(session, user, report_id)
    keys = data_rights.stored_keys(session, Report.id == report.id)
    test_ids = set(session.scalars(select(Observation.test_id).where(
        Observation.report_id == report.id, Observation.test_id.is_not(None), Observation.verified_at.is_not(None))))
    audit.record(session, user.id, "report.delete", "report", report.id)
    session.execute(delete(Report).where(Report.id == report.id))
    if test_ids:  # later reports may have used this one as their "previous" result
        analyse_profile(session, report.profile_id, test_ids)
    session.commit()
    data_rights.remove_objects(storage, keys)
