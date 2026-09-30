"""The analysis service on a real database: statuses, history-aware analysis, recomputation, the worker stage."""

from datetime import date

import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.models import Observation, ProcessingJob, Report, TrendInsight
from app.models.enums import JobStage, ObsStatus, ReportStatus, Sex
from app.services.analysis import POPULATION_LABEL, analyse_profile
from app.services.interpretation import lab_test_ids
from app.worker import queue
from app.worker.runner import Worker
from app.worker.stages import AnalysisStage
from tests.factories import add_report, make_profile

pytestmark = pytest.mark.db


def obs(s: Session, report: Report, code: str) -> Observation:
    ids = lab_test_ids(s)
    return s.scalar(select(Observation).where(Observation.report_id == report.id, Observation.test_id == ids[code]))


@pytest.fixture
def person(sessions: sessionmaker[Session]):
    with sessions.begin() as s:
        p = make_profile(s)
        p.sex = Sex.MALE
        p.date_of_birth = date(1980, 3, 1)
        return p.id, p.owner_user_id


def test_status_and_critical_limits(sessions: sessionmaker[Session], person) -> None:
    pid, uid = person
    with sessions.begin() as s:
        r = add_report(s, pid, uid, date(2026, 5, 1), {
            "hb": (12.1, 13.0, 17.0), "potassium": (6.6, 3.5, 5.1), "tsh": (2.1, None, None), "sodium": (139, 135, 145),
        })
        analyse_profile(s, pid)
        assert obs(s, r, "hb").status is ObsStatus.LOW
        assert obs(s, r, "potassium").status is ObsStatus.CRITICAL_HIGH
        assert obs(s, r, "tsh").status is ObsStatus.UNKNOWN  # no range printed and none given here
        assert obs(s, r, "sodium").status is ObsStatus.NORMAL
        assert obs(s, r, "hb").analysis["previous"] is None


def test_history_change_trend_and_percentile(sessions: sessionmaker[Session], person) -> None:
    pid, uid = person
    with sessions.begin() as s:
        reports = [add_report(s, pid, uid, date(2022 + i, 6, 1), {"hba1c": (v, 4.0, 6.5), "hb": (15.1, 13.0, 17.0)})
                   for i, v in enumerate([5.0, 5.3, 5.6, 5.9])]
        assert analyse_profile(s, pid) == 8
        latest = obs(s, reports[-1], "hba1c").analysis
        assert latest["previous"]["value"] == 5.6 and latest["previous"]["date"] == "2024-06-01"
        # No single step (+5.4 %) beats HbA1c's RCV (about +6.7 %), but four years rising together do.
        assert latest["change"]["significant"] is False
        assert latest["trend"]["confirmed"] is True and latest["trend"]["direction"] == "rising"
        assert latest["trend"]["projection"]["kind"] == "leave" and latest["trend"]["projection"]["limit"] == "high"
        # as-of analysis: the second report only sees two results, so no trend yet
        assert obs(s, reports[1], "hba1c").analysis["trend"] is None

        hb = obs(s, reports[-1], "hb").analysis["percentile"]
        assert hb["population"] == POPULATION_LABEL and hb["sex"] == "male" and hb["age_band"] == [40, 49]
        assert 40 <= hb["value"] <= 60  # 15.1 g/dL is the median for US men in their forties

        insight = s.scalar(select(TrendInsight).where(TrendInsight.profile_id == pid,
                                                      TrendInsight.test_id == lab_test_ids(s)["hba1c"]))
        assert insight.confirmed and insight.n_points == 4 and insight.projected_crossing is not None
        assert insight.last_observation_id == obs(s, reports[-1], "hba1c").id


def test_rcv_verdict_on_small_change(sessions: sessionmaker[Session], person) -> None:
    pid, uid = person
    with sessions.begin() as s:
        add_report(s, pid, uid, date(2025, 1, 1), {"hb": (14.0, 13.0, 17.0)})
        r = add_report(s, pid, uid, date(2025, 7, 1), {"hb": (14.5, 13.0, 17.0)})
        analyse_profile(s, pid)
        change = obs(s, r, "hb").analysis["change"]
        assert change["direction"] == "up" and change["significant"] is False
        assert change["rcv_up"] == pytest.approx(0.0831, abs=5e-4)


def test_late_older_report_becomes_the_previous_result(sessions: sessionmaker[Session], person) -> None:
    pid, uid = person
    with sessions.begin() as s:
        add_report(s, pid, uid, date(2024, 1, 1), {"creatinine": (0.9, 0.7, 1.3)})
        newest = add_report(s, pid, uid, date(2026, 1, 1), {"creatinine": (1.2, 0.7, 1.3)})
        analyse_profile(s, pid)
        assert obs(s, newest, "creatinine").analysis["previous"]["value"] == 0.9

        middle = add_report(s, pid, uid, date(2025, 1, 1), {"creatinine": (1.05, 0.7, 1.3)})
        analyse_profile(s, pid, {lab_test_ids(s)["creatinine"]})
        assert obs(s, newest, "creatinine").analysis["previous"]["value"] == 1.05
        assert obs(s, newest, "creatinine").analysis["trend"]["n"] == 3

        s.execute(delete(Report).where(Report.id == middle.id))
        analyse_profile(s, pid, {lab_test_ids(s)["creatinine"]})
        assert obs(s, newest, "creatinine").analysis["previous"]["value"] == 0.9


def test_insight_row_goes_when_the_last_result_goes(sessions: sessionmaker[Session], person) -> None:
    pid, uid = person
    with sessions.begin() as s:
        r = add_report(s, pid, uid, date(2025, 1, 1), {"alt": (30, None, 40)})
        analyse_profile(s, pid)
        assert s.scalar(select(TrendInsight).where(TrendInsight.profile_id == pid)) is not None
        s.execute(delete(Report).where(Report.id == r.id))
        analyse_profile(s, pid, {lab_test_ids(s)["alt"]})
        assert s.scalar(select(TrendInsight).where(TrendInsight.profile_id == pid)) is None


def test_worker_stage_analyses_then_queues_the_explanation(sessions: sessionmaker[Session], person) -> None:
    pid, uid = person
    with sessions.begin() as s:
        r = add_report(s, pid, uid, date(2025, 1, 1), {"hb": (12.0, 13.0, 17.0)})
        queue.enqueue(s, r.id, JobStage.ANALYSE)
        rid = r.id
    assert Worker(sessions, [AnalysisStage()]).run_once()
    with sessions.begin() as s:
        report = s.get(Report, rid)
        assert report.status is ReportStatus.EXPLAINING
        assert obs(s, report, "hb").status is ObsStatus.LOW
        stages = set(s.scalars(select(ProcessingJob.stage).where(ProcessingJob.report_id == rid)))
        assert stages == {JobStage.ANALYSE, JobStage.EXPLAIN}
