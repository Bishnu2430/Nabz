"""Where a value sits against its range (FR-16) and whether it crosses a critical limit (FR-17)."""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

from app.models.enums import ObsStatus

Number = Decimal | float | int

# Higher is worse. Orders organ cards and colours an organ by its worst test (FR-27).
SEVERITY = {
    ObsStatus.CRITICAL_LOW: 4,
    ObsStatus.CRITICAL_HIGH: 4,
    ObsStatus.LOW: 2,
    ObsStatus.HIGH: 2,
    ObsStatus.NORMAL: 0,
    ObsStatus.UNKNOWN: -1,
}

CRITICAL = frozenset({ObsStatus.CRITICAL_LOW, ObsStatus.CRITICAL_HIGH})


def classify(value: Number | None, low: Number | None, high: Number | None,
             critical_low: Number | None = None, critical_high: Number | None = None) -> ObsStatus:
    """Status of one value. Critical limits are checked first and apply even when the report prints no range.

    Limits are exclusive: a value equal to a range limit is in range ("13.0 – 17.0" includes 13.0), and a
    value equal to a critical limit is not critical.
    """
    if value is None:
        return ObsStatus.UNKNOWN
    if critical_low is not None and value < critical_low:
        return ObsStatus.CRITICAL_LOW
    if critical_high is not None and value > critical_high:
        return ObsStatus.CRITICAL_HIGH
    if low is None and high is None:
        return ObsStatus.UNKNOWN
    if low is not None and value < low:
        return ObsStatus.LOW
    if high is not None and value > high:
        return ObsStatus.HIGH
    return ObsStatus.NORMAL


def worst(statuses: Iterable[ObsStatus]) -> ObsStatus:
    """The most severe status; UNKNOWN when there is nothing to judge."""
    return max(statuses, key=lambda s: SEVERITY[s], default=ObsStatus.UNKNOWN)


def flag_disagrees(status: ObsStatus, printed_flag: str | None) -> bool:
    """True when the lab's printed H/L flag contradicts the computed status (worth showing; never trusted over it)."""
    if not printed_flag:
        return False
    flag = printed_flag.strip().upper()[:1]
    high = status in (ObsStatus.HIGH, ObsStatus.CRITICAL_HIGH)
    low = status in (ObsStatus.LOW, ObsStatus.CRITICAL_LOW)
    return (flag == "H" and not high) or (flag == "L" and not low)
