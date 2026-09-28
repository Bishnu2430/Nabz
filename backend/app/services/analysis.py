"""Analyse a person's confirmed results and store the outcome (FR-16 – FR-20).

Each result is analysed *as of its own date*: its status, the change since the previous result, the trend over
results up to that date, and its population percentile. Adding or deleting a report changes what "previous"
means for later reports (an older report uploaded late becomes their predecessor), so the unit of work is a
person × a set of tests, recomputed from scratch. That takes milliseconds at personal-history sizes.

Output:
- `observation.status` and `observation.analysis` (JSON, schema below) for every confirmed result;
- `trend_insight`, one row per person × test with the latest numbers, for the profile page.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.analysis.change import Change, compare, rcv
from app.analysis.percentile import Placement, age_band, place
from app.analysis.status import classify, flag_disagrees
from app.analysis.trend import Point, Trend, trend
from app.models import CriticalLimit, LabTest, Observation, PopulationPercentile, Profile, Report, TrendInsight
from app.services.interpretation import age_on

ANALYSIS_VERSION = 1
POPULATION_LABEL = "US population (NHANES 2017–2020)"


@dataclass(frozen=True)
class TestFacts:
    id: int
    code: str
    cv_within_subject: float | None
    cv_analytical: float | None
    critical_low: float | None
    critical_high: float | None


@dataclass(frozen=True)
class Result:
    obs: Observation
    report: Report
    when: date


def _f(v: Any) -> float | None:
    return None if v is None else float(v)


def result_date(report: Report) -> date:
    """The sample collection date, or the upload date when the report doesn't print one."""
    return report.collected_at or report.created_at.date()


def test_facts(session: Session) -> dict[int, TestFacts]:
    limits = {c.test_id: c for c in session.scalars(select(CriticalLimit))}
    facts = {}
    for t in session.scalars(select(LabTest)):
        lim = limits.get(t.id)
        facts[t.id] = TestFacts(t.id, t.code, t.cv_within_subject, t.cv_analytical,
                                _f(lim.low) if lim else None, _f(lim.high) if lim else None)
    return facts


class PercentileTable:
    """Population percentile cells keyed by test, sex (`unknown` = both sexes) and age band."""

    def __init__(self, session: Session):
        self.cells = {
            (p.test_id, p.sex.value, p.age_band.lower): tuple(float(c) for c in (p.p05, p.p25, p.p50, p.p75, p.p95))
            for p in session.scalars(select(PopulationPercentile))
        }

    def lookup(self, test_id: int, sex: str, age: int | None, value: float
               ) -> tuple[Placement, str, tuple[int, int]] | None:
        band = age_band(age)
        if band is None:
            return None
        key_sex = sex if sex in ("female", "male") else "unknown"
        cuts = self.cells.get((test_id, key_sex, band[0]))
        return (place(value, cuts), key_sex, band) if cuts else None


def history(session: Session, profile_id: uuid.UUID, test_ids: set[int] | None = None) -> dict[int, list[Result]]:
    """Confirmed results with a number, per test, oldest first."""
    q = (select(Observation, Report).join(Report, Report.id == Observation.report_id)
         .where(Report.profile_id == profile_id, Report.deleted_at.is_(None),
                Observation.verified_at.is_not(None), Observation.test_id.is_not(None),
                Observation.value_num.is_not(None)))
    if test_ids is not None:
        q = q.where(Observation.test_id.in_(test_ids))
    series: dict[int, list[Result]] = {}
    for obs, report in session.execute(q):
        series.setdefault(obs.test_id, []).append(Result(obs, report, result_date(report)))
    for results in series.values():
        results.sort(key=lambda r: (r.when, r.report.created_at, r.obs.created_at))
    return series


def analyse_profile(session: Session, profile_id: uuid.UUID, test_ids: set[int] | None = None) -> int:
    """Recompute the analysis for `test_ids` (all tests when None). Returns the number of results analysed."""
    profile = session.get(Profile, profile_id)
    if profile is None:
        return 0
    facts = test_facts(session)
    population = PercentileTable(session)
    series = history(session, profile_id, test_ids)
    now = datetime.now(UTC)
    analysed = 0

    for test_id, results in series.items():
        f = facts[test_id]
        limits = rcv(f.cv_analytical, f.cv_within_subject)
        latest_trend: Trend | None = None
        latest_change: Change | None = None
        latest_pct: float | None = None
        for i, r in enumerate(results):
            value = float(r.obs.value_num)
            low, high = _f(r.obs.ref_low), _f(r.obs.ref_high)
            r.obs.status = classify(value, low, high, f.critical_low, f.critical_high)

            previous = next((x for x in reversed(results[:i]) if x.when < r.when), None)
            change = compare(float(previous.obs.value_num), value, limits) if previous else None
            points = [Point(x.when, float(x.obs.value_num)) for x in results if x.when <= r.when]
            tr = trend(points, limits, low, high)
            found = population.lookup(test_id, profile.sex.value, age_on(profile, r.when), value)

            r.obs.analysis = {
                "version": ANALYSIS_VERSION,
                "as_of": r.when.isoformat(),
                "flag_disagrees": flag_disagrees(r.obs.status, r.obs.raw_flag),
                "previous": None if previous is None else {
                    "value": float(previous.obs.value_num), "date": previous.when.isoformat(),
                    "report_id": str(previous.report.id),
                },
                "change": None if change is None else _change_json(change),
                "trend": None if tr is None else _trend_json(tr),
                "percentile": None if found is None else {
                    "value": found[0].percentile, "side": found[0].side, "population": POPULATION_LABEL,
                    "sex": found[1], "age_band": list(found[2]),
                },
            }
            latest_trend, latest_change = tr, change
            latest_pct = found[0].percentile if found else None
            analysed += 1

        last = results[-1]
        values = {
            "last_observation_id": last.obs.id, "n_points": len(results),
            "slope_per_year": latest_trend.slope_per_year if latest_trend else None,
            "direction": latest_trend.direction if latest_trend else None,
            "confirmed": bool(latest_trend and latest_trend.confirmed),
            "rcv_significant": latest_change.significant if latest_change else None,
            "projected_crossing": latest_trend.projection.on if latest_trend and latest_trend.projection else None,
            "percentile": latest_pct, "computed_at": now,
        }
        stmt = insert(TrendInsight).values(profile_id=profile_id, test_id=test_id, **values)
        session.execute(stmt.on_conflict_do_update(constraint="uq_trend_insight_profile_test", set_=values))

    # Tests left with no confirmed results (their report was deleted) lose their insight row.
    stale = delete(TrendInsight).where(TrendInsight.profile_id == profile_id,
                                       TrendInsight.test_id.not_in(list(series) or [-1]))
    if test_ids is not None:
        stale = stale.where(TrendInsight.test_id.in_(test_ids))
    session.execute(stale)
    session.flush()
    return analysed


def _round(v: float | None, digits: int = 6) -> float | None:
    return None if v is None else float(f"{v:.{digits}g}")


def _change_json(c: Change) -> dict[str, Any]:
    return {
        "fraction": _round(c.fraction), "direction": c.direction, "significant": c.significant,
        "rcv_down": _round(c.rcv.down) if c.rcv else None, "rcv_up": _round(c.rcv.up) if c.rcv else None,
    }


def _trend_json(t: Trend) -> dict[str, Any]:
    return {
        "n": t.n, "first": t.first.isoformat(), "last": t.last.isoformat(),
        "slope_per_year": _round(t.slope_per_year), "intercept": _round(t.intercept),
        "slope_low": _round(t.slope_low), "slope_high": _round(t.slope_high), "p_value": _round(t.p_value, 4),
        "change_fraction": _round(t.change_fraction), "direction": t.direction, "confirmed": t.confirmed,
        "reason": t.reason,
        "projection": None if t.projection is None else {
            "kind": t.projection.kind, "limit": t.projection.limit, "value": _round(t.projection.value),
            "on": t.projection.on.isoformat(),
        },
    }
