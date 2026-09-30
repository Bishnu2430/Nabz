"""The de-identified input to an explanation (FR-25).

Only what the text needs leaves the database: test, value, unit, range, computed status, the change since the
previous result, the trend and the percentile, plus the person's age band and sex. No names, identifiers, dates
or free text from the report go to an external model. Intervals are expressed in months instead of dates.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis.percentile import age_band
from app.analysis.status import CRITICAL, SEVERITY
from app.catalogue.symptoms import symptoms_for
from app.models import LabTest, Observation, OrganSystem, Profile, Report
from app.models.enums import ObsStatus
from app.services.analysis import result_date
from app.services.interpretation import age_on

MAX_FOCUS = 8  # tests explained in detail (worst first); the summary covers the rest


@dataclass
class TestItem:
    test_code: str
    test: str
    organ: str
    value: float
    unit: str | None
    range_low: float | None
    range_high: float | None
    range_source: str  # "lab" | "typical"
    status: str
    change: dict[str, Any] | None = None
    trend: dict[str, Any] | None = None
    percentile: dict[str, Any] | None = None
    # For out-of-range results: {"kind": symptoms|often_none|none, "can_go_along_with": [...]} (MedlinePlus)
    symptoms: dict[str, Any] | None = None

    @property
    def out_of_range(self) -> bool:
        return self.status not in (ObsStatus.NORMAL, ObsStatus.UNKNOWN)

    @property
    def is_focus(self) -> bool:
        """Worth explaining in detail: out of range, changed significantly, or trending."""
        return (self.status not in (ObsStatus.NORMAL, ObsStatus.UNKNOWN)
                or bool(self.change and self.change.get("significant"))
                or bool(self.trend and self.trend.get("confirmed")))


@dataclass
class Payload:
    age_band: str | None
    sex: str
    results_total: int
    outside_range: int
    focus: list[TestItem] = field(default_factory=list)
    others: list[str] = field(default_factory=list)  # names of the remaining tests, all in range or unjudged
    critical: list[str] = field(default_factory=list)  # test codes beyond a critical limit

    def to_json(self) -> str:
        data = asdict(self)
        data.pop("critical")
        return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def _f(v: Decimal | None, places: int | None = None) -> float | None:
    if v is None:
        return None
    return round(float(v), places) if places is not None else float(v)


def _population(pc: dict[str, Any]) -> str:
    group = {"male": "men", "female": "women"}.get(pc["sex"], "adults")
    lo, hi = pc["age_band"]
    return f"US {group} aged {lo}+" if hi >= 120 else f"US {group} aged {lo}–{hi}"


def _months(a: date, b: date) -> int:
    return max(1, round((b - a).days / 30.44))


def build_payload(session: Session, report: Report) -> Payload:
    profile = session.get(Profile, report.profile_id)
    tests = {t.id: t for t in session.scalars(select(LabTest))}
    organs = {o.id: o.code for o in session.scalars(select(OrganSystem))}
    rows = session.scalars(select(Observation).where(
        Observation.report_id == report.id, Observation.test_id.is_not(None), Observation.value_num.is_not(None),
        Observation.verified_at.is_not(None))).all()
    when = result_date(report)
    band = age_band(age_on(profile, when)) if profile else None

    items: list[TestItem] = []
    for o in rows:
        t = tests[o.test_id]
        a = o.analysis or {}
        item = TestItem(
            test_code=t.code, test=t.canonical_name, organ=organs[t.organ_system_id],
            value=_f(o.value_num, t.decimals), unit=o.unit, range_low=_f(o.ref_low), range_high=_f(o.ref_high),
            range_source="lab" if o.ref_source == "report" else "typical", status=o.status.value,
        )
        if (ch := a.get("change")) and ch.get("fraction") is not None and (prev := a.get("previous")):
            item.change = {
                "percent": round(ch["fraction"] * 100), "direction": ch["direction"],
                "significant": ch["significant"], "previous_value": round(prev["value"], t.decimals),
                "months_since_previous": _months(date.fromisoformat(prev["date"]), when),
            }
        if tr := a.get("trend"):
            span = date.fromisoformat(tr["last"]) - date.fromisoformat(tr["first"])
            item.trend = {"direction": tr["direction"], "confirmed": tr["confirmed"], "results": tr["n"],
                          "years": round(span.days / 365.25)}
            if tr["confirmed"] and (pj := tr.get("projection")):
                item.trend["projection"] = {"kind": pj["kind"], "limit": pj["limit"], "limit_value": pj["value"],
                                            "months_ahead": _months(when, date.fromisoformat(pj["on"]))}
        if pc := a.get("percentile"):
            item.percentile = {"value": round(pc["value"]), "side": pc["side"], "population": _population(pc)}
        if item.out_of_range and (sy := symptoms_for(item.test_code, item.status)):
            item.symptoms = {"kind": sy.kind, "can_go_along_with": list(sy.for_language("en"))}
        items.append(item)

    items.sort(key=lambda i: (-SEVERITY[ObsStatus(i.status)], i.test))
    critical = [i.test_code for i in items if ObsStatus(i.status) in CRITICAL]
    focus = [i for i in items if i.is_focus][:MAX_FOCUS]
    focus_codes = {i.test_code for i in focus}
    return Payload(
        age_band=None if band is None else (f"{band[0]}+" if band[1] >= 120 else f"{band[0]}–{band[1]}"),
        sex=profile.sex.value if profile else "unknown",
        results_total=len(items),
        outside_range=sum(ObsStatus(i.status) not in (ObsStatus.NORMAL, ObsStatus.UNKNOWN) for i in items),
        focus=focus,
        others=[i.test for i in items if i.test_code not in focus_codes],
        critical=critical,
    )


_NUMBER = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)?")


def allowed_numbers(payload: Payload) -> set[str]:
    """Every number the explanation may mention, in the renderings a writer would use."""
    found: set[str] = set()
    for token in _NUMBER.findall(payload.to_json()):
        found |= renderings(token)
    return found


def renderings(token: str) -> set[str]:
    """"1.10" -> {"1.1", "1.10", "1"}; "17" -> {"17"}; "0.152" -> {"0.152", "0.15", "0.2", "0"} …"""
    token = token.replace(",", ".")
    value = float(token)
    out = {normalise(token)}
    for places in (0, 1, 2):
        out.add(normalise(f"{value:.{places}f}"))
    return out


def normalise(token: str) -> str:
    token = token.replace(",", ".")
    if "." in token:
        token = token.rstrip("0").rstrip(".")
    return token or "0"
