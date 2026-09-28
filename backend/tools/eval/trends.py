"""Evaluate change significance and trend confirmation on synthetic histories with a planted drift.

    python -m tools.synthetic --count 0 --histories 50 --visits 5 --seed 21 --out /srv/data/synthetic/histories
    python -m tools.eval.trends --dir /srv/data/synthetic/histories

Each history person has yearly reports. Every value varies around a personal baseline by the test's within-subject
variation, and one test drifts at a planted slope (`planted_trend` in the ground truth). The analysis runs on
the ground-truth values (extraction is measured separately), using the first k visits for k = 3, 4, 5:

- **Power:** the planted test's trend is confirmed, in the right direction.
- **False alarms:** another test's trend is confirmed. Tests computed from the drifting one (eAG from HbA1c,
  eGFR from creatinine, …) are excluded, because they really do drift.
- **Coverage:** the planted slope lies inside Sen's 90 % interval.
- **Slope error:** median |estimated − planted| / planted.
- **RCV false positives:** consecutive results of non-drifting tests flagged as a significant change. By
  design this should stay under 5 %; the generator adds within-subject variation only.

Headline rates use *primary* tests only. The generator computes some tests from others that vary independently
(MCV = Hct / RBC, Friedewald LDL, the differential, …), so those vary more than they do in a real person and
say more about the generator than about the analysis. Rates over all tests are reported alongside.
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from datetime import date
from pathlib import Path

from app.analysis.change import compare, rcv
from app.analysis.trend import Point, trend
from app.catalogue import read_catalogue
from app.core.config import settings

# Tests computed from another test in the generator: they drift with it.
DERIVED_FROM = {
    "hba1c": {"eag"},
    "creatinine": {"egfr"},
    "hb": {"hct", "mcv", "mch", "mchc"},
    "chol_total": {"ldl", "non_hdl", "chol_hdl_ratio"},
    "alt": set(),
    "tsh": set(),
}

# Computed by the generator from other tests (tools/synthetic/values.py), so their visit-to-visit variation
# is not physiological.
GENERATOR_DERIVED = {
    "hct", "mcv", "mch", "mchc", "neut_pct", "lymph_pct", "mono_pct", "eos_pct", "baso_pct", "eag", "vldl", "ldl",
    "non_hdl", "chol_hdl_ratio", "bun", "egfr", "bili_indirect", "globulin", "ag_ratio", "tsat",
}


def load_histories(directory: Path) -> dict[str, list[dict]]:
    people: dict[str, list[dict]] = defaultdict(list)
    for path in sorted(directory.glob("hist-*.json")):
        truth = json.loads(path.read_text(encoding="utf-8"))
        people[truth["person_id"]].append(truth)
    for visits in people.values():
        visits.sort(key=lambda t: t["visit"])
    return people


def evaluate(directory: Path, visit_counts: tuple[int, ...] = (3, 4, 5)) -> dict:
    cat = read_catalogue(Path(settings.data_dir) / "catalogue")
    limits = {t.code: rcv(t.cv_a, t.cv_i) for t in cat.tests}
    people = load_histories(directory)
    out: dict = {"people": len(people), "by_visits": {}}

    for k in visit_counts:
        power = coverage = n_planted = 0
        false_alarm = n_other = 0
        false_alarm_primary = n_primary = 0
        slope_errors: list[float] = []
        for visits in people.values():
            if len(visits) < k:
                continue
            planted = visits[0]["planted_trend"]
            series: dict[str, list[Point]] = defaultdict(list)
            ranges: dict[str, tuple[float | None, float | None]] = {}
            for v in visits[:k]:
                when = date.fromisoformat(v["collected_at"])
                for row in v["rows"]:
                    series[row["test_code"]].append(Point(when, float(row["value_canonical"])))
                    ranges[row["test_code"]] = (_num(row.get("ref_low")), _num(row.get("ref_high")))
            skip = DERIVED_FROM.get(planted["test_code"], set())
            for code, points in series.items():
                t = trend(points, limits.get(code), *ranges[code])
                if t is None:
                    continue
                if code == planted["test_code"]:
                    n_planted += 1
                    expected = "rising" if planted["slope_per_year"] > 0 else "falling"
                    power += t.confirmed and t.direction == expected
                    if t.slope_low is not None and t.slope_high is not None:
                        coverage += t.slope_low <= planted["slope_per_year"] <= t.slope_high
                    slope_errors.append(abs(t.slope_per_year - planted["slope_per_year"])
                                        / abs(planted["slope_per_year"]))
                elif code not in skip:
                    n_other += 1
                    false_alarm += t.confirmed
                    if code not in GENERATOR_DERIVED:
                        n_primary += 1
                        false_alarm_primary += t.confirmed
        out["by_visits"][k] = {
            "planted_series": n_planted,
            "power": _share(power, n_planted),
            "coverage_90": _share(coverage, n_planted),
            "median_slope_error": round(statistics.median(slope_errors), 3) if slope_errors else None,
            "false_alarm_rate": _share(false_alarm_primary, n_primary),
            "primary_series": n_primary,
            "false_alarm_rate_all_tests": _share(false_alarm, n_other),
            "all_series": n_other,
        }

    flagged = pairs = flagged_all = pairs_all = 0
    for visits in people.values():
        planted = visits[0]["planted_trend"]["test_code"]
        skip = DERIVED_FROM.get(planted, set()) | {planted}
        by_test: dict[str, list[float]] = defaultdict(list)
        for v in visits:
            for row in v["rows"]:
                by_test[row["test_code"]].append(float(row["value_canonical"]))
        for code, values in by_test.items():
            if code in skip or limits.get(code) is None:
                continue
            for prev, cur in zip(values, values[1:], strict=False):
                c = compare(prev, cur, limits[code])
                if c.significant is None:
                    continue
                pairs_all += 1
                flagged_all += c.significant
                if code not in GENERATOR_DERIVED:
                    pairs += 1
                    flagged += c.significant
    out["rcv_false_positive_rate"] = _share(flagged, pairs)
    out["rcv_pairs"] = pairs
    out["rcv_false_positive_rate_all_tests"] = _share(flagged_all, pairs_all)
    out["rcv_pairs_all_tests"] = pairs_all

    by_test_power: dict[str, list[bool]] = defaultdict(list)
    k = max(visit_counts)
    for visits in people.values():
        if len(visits) < k:
            continue
        planted = visits[0]["planted_trend"]
        points = [Point(date.fromisoformat(v["collected_at"]), float(r["value_canonical"]))
                  for v in visits[:k] for r in v["rows"] if r["test_code"] == planted["test_code"]]
        t = trend(points, limits.get(planted["test_code"]))
        by_test_power[planted["test_code"]].append(bool(t and t.confirmed))
    out["power_by_test_at_max_visits"] = {c: {"people": len(v), "power": _share(sum(v), len(v))}
                                          for c, v in sorted(by_test_power.items())}
    return out


def _num(v: str | None) -> float | None:
    return None if v in (None, "") else float(v)


def _share(a: int, b: int) -> float | None:
    return round(a / b, 3) if b else None


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m tools.eval.trends")
    ap.add_argument("--dir", default=str(Path(settings.data_dir) / "synthetic" / "histories"))
    ap.add_argument("--out")
    a = ap.parse_args()
    result = evaluate(Path(a.dir))
    text = json.dumps(result, indent=2)
    print(text)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
