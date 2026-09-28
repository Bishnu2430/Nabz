"""Where a value sits in a reference population (FR-20).

The population table holds the 5th, 25th, 50th, 75th and 95th percentiles per test, sex and age band
(built from NHANES by tools.nhanes). A value between two cut points gets a linearly interpolated
percentile. Values beyond the 5th or 95th percentile are reported as "below 5" / "above 95", because the
table says nothing finer out there.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

LEVELS = (5, 25, 50, 75, 95)

# NHANES reports age in whole years, top-coded at 80.
AGE_BANDS = ((18, 29), (30, 39), (40, 49), (50, 59), (60, 69), (70, 79), (80, 120))


@dataclass(frozen=True)
class Placement:
    percentile: float  # 5–95; the bound itself when outside
    side: str  # "below" | "within" | "above"


def age_band(age: int | None) -> tuple[int, int] | None:
    if age is None:
        return None
    return next((b for b in AGE_BANDS if b[0] <= age <= b[1]), None)


def place(value: float, cuts: Sequence[float]) -> Placement:
    """Percentile of `value` given the cut points at LEVELS (ascending)."""
    if len(cuts) != len(LEVELS):
        raise ValueError(f"expected {len(LEVELS)} cut points")
    if value < cuts[0]:
        return Placement(LEVELS[0], "below")
    if value > cuts[-1]:
        return Placement(LEVELS[-1], "above")
    steps = zip(LEVELS, LEVELS[1:], strict=False)
    spans = zip(cuts, cuts[1:], strict=False)
    for (lo_p, hi_p), (lo_v, hi_v) in zip(steps, spans, strict=True):
        if lo_v <= value <= hi_v:
            if hi_v == lo_v:
                return Placement((lo_p + hi_p) / 2, "within")
            return Placement(round(lo_p + (value - lo_v) / (hi_v - lo_v) * (hi_p - lo_p), 1), "within")
    return Placement(LEVELS[-1], "above")  # unreachable for ascending cuts
