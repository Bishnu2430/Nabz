"""Analysis results: a report's insights, one test's history, and what to watch for a person (FR-16 – FR-20)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis.change import rcv
from app.analysis.status import CRITICAL, SEVERITY, worst
from app.api.deps import current_user, get_session, owned_profile, owned_report
from app.models import AppUser, LabTest, Observation, OrganSystem, Profile, Report, TrendInsight
from app.models.enums import ReportStatus
from app.schemas import (
    BodyMapFrame,
    BodyMapOrgan,
    InsightsOut,
    OrganHistoryOut,
    OrganOut,
    OrganTestHistory,
    PersonOut,
    ReportSummary,
    ResultOut,
    TestHistoryOut,
    TestInfoOut,
    WatchOut,
)
from app.services.analysis import history, result_date
from app.services.briefs import brief, worst_first
from app.services.interpretation import age_on

router = APIRouter(tags=["insights"])


class _Catalogue:
    """Tests and organ systems, loaded once per request."""

    def __init__(self, session: Session):
        self.tests = {t.id: t for t in session.scalars(select(LabTest))}
        self.organs = {o.id: o for o in session.scalars(select(OrganSystem))}

    def organ_code(self, test: LabTest) -> str:
        return self.organs[test.organ_system_id].code


def _person(profile: Profile, report: Report | None = None) -> PersonOut:
    return PersonOut(id=profile.id, display_name=profile.display_name, sex=profile.sex,
                     age=age_on(profile, result_date(report) if report else None))


def _result(obs: Observation, report: Report, cat: _Catalogue) -> ResultOut:
    test = cat.tests[obs.test_id]
    a: dict[str, Any] = obs.analysis or {}
    return ResultOut(
        observation_id=obs.id, report_id=report.id, date=result_date(report), test_code=test.code,
        test_name=test.canonical_name, short_name=test.short_name, organ=cat.organ_code(test), value=obs.value_num,
        unit=obs.unit, decimals=test.decimals, ref_low=obs.ref_low, ref_high=obs.ref_high, ref_source=obs.ref_source,
        status=obs.status, critical=obs.status in CRITICAL, flag_disagrees=a.get("flag_disagrees", False),
        previous=a.get("previous"), change=a.get("change"), trend=a.get("trend"), percentile=a.get("percentile"),
    )


def _severity_then_catalogue(r: ResultOut, cat: _Catalogue, ids: dict[str, int]) -> tuple[int, int]:
    return (-SEVERITY[r.status], ids[r.test_code])


@router.get("/v1/reports/{report_id}/insights", response_model=InsightsOut)
def report_insights(report_id: uuid.UUID, session: Session = Depends(get_session),  # noqa: B008
                    user: AppUser = Depends(current_user)):  # noqa: B008
    report = owned_report(session, user, report_id)
    profile = session.get(Profile, report.profile_id)
    cat = _Catalogue(session)
    ids = {t.code: t.id for t in cat.tests.values()}
    rows = session.scalars(select(Observation).where(Observation.report_id == report.id,
                                                     Observation.test_id.is_not(None),
                                                     Observation.value_num.is_not(None))).all()
    results = sorted((_result(o, report, cat) for o in rows), key=lambda r: _severity_then_catalogue(r, cat, ids))

    by_organ: dict[str, list[ResultOut]] = {}
    for r in results:
        by_organ.setdefault(r.organ, []).append(r)
    organ_rows = {o.code: o for o in cat.organs.values()}
    organs = [
        OrganOut(code=code, names={"en": organ_rows[code].name_en, "hi": organ_rows[code].name_hi,
                                   "or": organ_rows[code].name_or},
                 status=worst(r.status for r in items), results=items)
        for code, items in by_organ.items()
    ]
    organs.sort(key=lambda o: (-SEVERITY[o.status], organ_rows[o.code].id))

    return InsightsOut(
        report=ReportSummary(id=report.id, status=report.status, lab_name=report.lab_name,
                             collected_at=report.collected_at, created_at=report.created_at, rows=len(rows)),
        person=_person(profile, report),
        analysed=any(o.analysis is not None for o in rows),
        critical=[r for r in results if r.critical],
        organs=organs,
    )


@router.get("/v1/profiles/{profile_id}/tests/{test_code}", response_model=TestHistoryOut)
def test_history(profile_id: uuid.UUID, test_code: str, session: Session = Depends(get_session),  # noqa: B008
                 user: AppUser = Depends(current_user)):  # noqa: B008
    profile = owned_profile(session, user, profile_id)
    test = session.scalar(select(LabTest).where(LabTest.code == test_code))
    if test is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Test not found.")
    cat = _Catalogue(session)
    limits = rcv(test.cv_analytical, test.cv_within_subject)
    series = history(session, profile.id, {test.id}).get(test.id, [])
    return TestHistoryOut(
        test=TestInfoOut(code=test.code, name=test.canonical_name, short_name=test.short_name,
                         unit=test.canonical_unit, decimals=test.decimals, organ=cat.organ_code(test),
                         rcv_down=limits.down if limits else None, rcv_up=limits.up if limits else None),
        person=_person(profile),
        results=[_result(r.obs, r.report, cat) for r in series],
    )


@router.get("/v1/profiles/{profile_id}/watch", response_model=list[WatchOut])
def watch_list(profile_id: uuid.UUID, session: Session = Depends(get_session),  # noqa: B008
               user: AppUser = Depends(current_user)):  # noqa: B008
    """Tests whose latest result has a confirmed trend or a significant change since the previous one."""
    profile = owned_profile(session, user, profile_id)
    cat = _Catalogue(session)
    rows = session.execute(
        select(TrendInsight, Observation, Report)
        .join(Observation, Observation.id == TrendInsight.last_observation_id)
        .join(Report, Report.id == Observation.report_id)
        .where(TrendInsight.profile_id == profile.id,
               (TrendInsight.confirmed.is_(True)) | (TrendInsight.rcv_significant.is_(True)))
    ).all()
    items = [
        WatchOut(test_code=cat.tests[t.test_id].code, test_name=cat.tests[t.test_id].canonical_name,
                 organ=cat.organ_code(cat.tests[t.test_id]), n_points=t.n_points, direction=t.direction,
                 confirmed=t.confirmed, rcv_significant=t.rcv_significant, projected_crossing=t.projected_crossing,
                 percentile=t.percentile, latest=_result(obs, report, cat))
        for t, obs, report in rows
    ]
    items.sort(key=lambda w: (not w.confirmed, -SEVERITY[w.latest.status], w.test_name))
    return items


ANALYSED = (ReportStatus.VERIFIED, ReportStatus.ANALYSING, ReportStatus.EXPLAINING, ReportStatus.EXPLAINED)


@router.get("/v1/profiles/{profile_id}/body-map", response_model=list[BodyMapFrame])
def body_map(profile_id: uuid.UUID, session: Session = Depends(get_session),  # noqa: B008
             user: AppUser = Depends(current_user)):  # noqa: B008
    """Each confirmed report's organ systems and their worst status, oldest first (FR-27, FR-29)."""
    profile = owned_profile(session, user, profile_id)
    cat = _Catalogue(session)
    rows = session.execute(
        select(Report, Observation)
        .join(Observation, Observation.report_id == Report.id)
        .where(Report.profile_id == profile.id, Report.deleted_at.is_(None), Report.status.in_(ANALYSED),
               Observation.test_id.is_not(None), Observation.value_num.is_not(None),
               Observation.verified_at.is_not(None))
    ).all()
    reports: dict[uuid.UUID, Report] = {}
    results: dict[uuid.UUID, dict[str, list]] = {}
    for report, obs in rows:
        reports[report.id] = report
        test = cat.tests[obs.test_id]
        results.setdefault(report.id, {}).setdefault(cat.organ_code(test), []).append(brief(obs, test, report))
    frames = []
    for rid, by_organ in results.items():
        organs = [BodyMapOrgan(code=code, status=worst(b.status for b in items), results=len(items),
                               out_of_range=sum(SEVERITY[b.status] > 0 for b in items), tests=worst_first(items))
                  for code, items in by_organ.items()]
        organs.sort(key=lambda o: (-SEVERITY[o.status], o.code))
        report = reports[rid]
        frames.append(BodyMapFrame(report_id=rid, date=result_date(report), lab_name=report.lab_name, organs=organs))
    frames.sort(key=lambda f: (f.date, reports[f.report_id].created_at))
    return frames


@router.get("/v1/profiles/{profile_id}/organs/{organ_code}", response_model=OrganHistoryOut)
def organ_history(profile_id: uuid.UUID, organ_code: str, session: Session = Depends(get_session),  # noqa: B008
                  user: AppUser = Depends(current_user)):  # noqa: B008
    """Every test of one organ system with all its confirmed results and their as-of analysis (FR-28)."""
    profile = owned_profile(session, user, profile_id)
    cat = _Catalogue(session)
    organ = next((o for o in cat.organs.values() if o.code == organ_code), None)
    if organ is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organ system not found.")
    test_ids = {t.id for t in cat.tests.values() if t.organ_system_id == organ.id}
    tests = []
    for test_id, series in history(session, profile.id, test_ids).items():
        test = cat.tests[test_id]
        limits = rcv(test.cv_analytical, test.cv_within_subject)
        tests.append(OrganTestHistory(
            test=TestInfoOut(code=test.code, name=test.canonical_name, short_name=test.short_name,
                             unit=test.canonical_unit, decimals=test.decimals, organ=organ.code,
                             rcv_down=limits.down if limits else None, rcv_up=limits.up if limits else None),
            results=[_result(r.obs, r.report, cat) for r in series],
        ))
    order = {t.code: t.id for t in cat.tests.values()}
    tests.sort(key=lambda h: (-SEVERITY[h.results[-1].status], order[h.test.code]))
    return OrganHistoryOut(code=organ.code, names={"en": organ.name_en, "hi": organ.name_hi, "or": organ.name_or},
                           person=_person(profile), tests=tests)
