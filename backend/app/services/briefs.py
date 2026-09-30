"""One-line result summaries used across the app (report lists, family cards, body-map frames)."""

from __future__ import annotations

from app.analysis.status import SEVERITY
from app.models import LabTest, Observation, Report
from app.schemas import ResultBrief
from app.services.analysis import result_date


def brief(obs: Observation, test: LabTest, report: Report) -> ResultBrief:
    return ResultBrief(test_code=test.code, test_name=test.canonical_name, short_name=test.short_name,
                       value=obs.value_num, unit=obs.unit, decimals=test.decimals, status=obs.status,
                       ref_low=obs.ref_low, ref_high=obs.ref_high, date=result_date(report), report_id=report.id)


def worst_first(items: list[ResultBrief]) -> list[ResultBrief]:
    """Most severe first; within a severity, the result furthest outside its range first."""
    def distance(b: ResultBrief) -> float:
        v = float(b.value)
        if b.ref_high is not None and v > float(b.ref_high) and float(b.ref_high):
            return v / float(b.ref_high) - 1
        if b.ref_low is not None and v < float(b.ref_low) and float(b.ref_low):
            return 1 - v / float(b.ref_low)
        return 0.0
    return sorted(items, key=lambda b: (-SEVERITY[b.status], -distance(b), b.test_name))
