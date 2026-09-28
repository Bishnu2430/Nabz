"""Is the change since the previous result bigger than normal variation? (FR-18)

Two results of the same test differ even in a healthy, stable person: the body varies from day to day
(within-subject variation, CVi) and so does the lab's measurement (analytical variation, CVa). The reference
change value (RCV) is the smallest change that those two alone would produce less than 5 % of the time.

Nabz uses the log-normal, asymmetric RCV (Fokkema et al., Clin Chem 2006;52:329–35). Lab values are positive
and their variation grows with the value, so a rise must be a little larger than a fall to be significant:

    sigma    = sqrt( ln(1 + CVa²) + ln(1 + CVi²) )        CVs as fractions
    RCV_up   = exp( +Z·√2·sigma ) − 1
    RCV_down = exp( −Z·√2·sigma ) − 1                  Z = 1.96, two-sided 95 %

CVi and CVa come from the catalogue (EFLM Biological Variation Database). Tests without CVi get no verdict.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

Z_95 = 1.96


@dataclass(frozen=True)
class Rcv:
    down: float  # fraction, negative (−0.11 = an 11 % fall)
    up: float  # fraction, positive


@dataclass(frozen=True)
class Change:
    previous: float
    current: float
    fraction: float | None  # current / previous − 1; None when either value is not positive
    rcv: Rcv | None
    significant: bool | None  # None when the test has no RCV or the change can't be expressed as a ratio

    @property
    def direction(self) -> str:
        if self.current > self.previous:
            return "up"
        if self.current < self.previous:
            return "down"
        return "none"


def rcv(cv_analytical: float | None, cv_within_subject: float | None, z: float = Z_95) -> Rcv | None:
    """RCV from CVs in percent. A missing CVa counts as 0; CVi is essential."""
    if cv_within_subject is None or cv_within_subject <= 0:
        return None
    cva = (cv_analytical or 0.0) / 100
    cvi = cv_within_subject / 100
    sigma = math.sqrt(math.log1p(cva**2) + math.log1p(cvi**2))
    k = z * math.sqrt(2) * sigma
    return Rcv(down=math.expm1(-k), up=math.expm1(k))


def compare(previous: float, current: float, limits: Rcv | None) -> Change:
    if previous <= 0 or current <= 0:
        return Change(previous, current, None, limits, None)
    fraction = current / previous - 1
    significant = None if limits is None else (fraction > limits.up or fraction < limits.down)
    return Change(previous, current, fraction, limits, significant)
