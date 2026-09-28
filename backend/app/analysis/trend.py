"""Robust trend over a person's results for one test (FR-19).

- **Slope:** Theil–Sen, the median of all pairwise slopes, in canonical units per year. One odd result
  can't swing it the way it swings a least-squares line.
- **Interval:** Sen's (1968) 90 % confidence interval for the slope, computed the same way as
  scipy.stats.theilslopes.
- **Significance:** Mann–Kendall S with its exact null distribution (Kendall's tau counts pairs in time
  order that rise versus fall), two-sided.

A trend is **confirmed** only when all of these hold:
1. There are at least MIN_POINTS results spanning at least MIN_SPAN_DAYS.
2. Mann–Kendall p < ALPHA. With three results this is impossible (the smallest p is 1/3), so a
   direction needs a fourth result to be confirmed.
3. The change the fitted line implies over the span is larger than the test's reference change value,
   so it exceeds what biological and analytical variation alone produce. Tests without biological-variation
   data have no RCV and are never confirmed: the direction is shown, but statistics alone would raise a
   false alarm for about one noisy series in twelve (four results rising by chance).

For a confirmed trend, the line is extended at most HORIZON_YEARS to say when it would cross a range limit
("leave") or come back inside ("enter"). This is arithmetic on past results, not a prediction; the UI says so.
"""

from __future__ import annotations

import math
import statistics
from collections import Counter
from dataclasses import dataclass, replace
from datetime import date, timedelta
from functools import lru_cache

from app.analysis.change import Rcv

MIN_POINTS = 3
MIN_SPAN_DAYS = 180
ALPHA = 0.10
CONFIDENCE = 0.90
HORIZON_YEARS = 5.0
DAYS_PER_YEAR = 365.25


@dataclass(frozen=True)
class Point:
    when: date
    value: float


@dataclass(frozen=True)
class Projection:
    kind: str  # "leave" (moving out of range) | "enter" (moving back into range)
    limit: str  # "low" | "high"
    value: float  # the range limit it reaches
    on: date


@dataclass(frozen=True)
class Trend:
    n: int
    first: date
    last: date
    slope_per_year: float
    intercept: float  # fitted value at `first`
    slope_low: float | None  # 90 % confidence interval (Sen 1968)
    slope_high: float | None
    p_value: float  # Mann–Kendall, two-sided
    change_fraction: float | None  # fitted(last) / fitted(first) − 1
    direction: str  # "rising" | "falling" | "flat"
    confirmed: bool
    reason: str  # why not confirmed: too_few | short_span | not_significant | no_variation_data | within_variation
    projection: Projection | None

    def fitted(self, when: date) -> float:
        return self.intercept + self.slope_per_year * _years(self.first, when)


def _years(start: date, when: date) -> float:
    return (when - start).days / DAYS_PER_YEAR


def _sign(v: float) -> int:
    return (v > 0) - (v < 0)


def theil_sen(xs: list[float], ys: list[float], confidence: float = CONFIDENCE
              ) -> tuple[float, float, float | None, float | None]:
    """(slope, intercept, low, high). Intercept is Sen's median(y − slope·x). Pairs with equal x are skipped."""
    slopes = sorted((ys[j] - ys[i]) / (xs[j] - xs[i])
                    for i in range(len(xs)) for j in range(len(xs)) if xs[j] > xs[i])
    if not slopes:
        raise ValueError("need at least two distinct x values")
    slope = statistics.median(slopes)
    intercept = statistics.median(y - slope * x for x, y in zip(xs, ys, strict=True))

    z = abs(statistics.NormalDist().inv_cdf((1 - confidence) / 2))
    n, nt = len(ys), len(slopes)
    ties = [k for k in (*Counter(xs).values(), *Counter(ys).values()) if k > 1]
    var = (n * (n - 1) * (2 * n + 5) - sum(k * (k - 1) * (2 * k + 5) for k in ties)) / 18
    if var <= 0:
        return slope, intercept, None, None
    sigma = math.sqrt(var)
    upper = min(round((nt + z * sigma) / 2), nt - 1)
    lower = max(round((nt - z * sigma) / 2) - 1, 0)
    return slope, intercept, slopes[lower], slopes[upper]


@lru_cache(maxsize=64)
def _kendall_null(n: int) -> tuple[int, ...]:
    """Number of permutations of n items with k inversions (Mahonian numbers), k = 0 … n(n−1)/2."""
    counts = [1]
    for m in range(2, n + 1):
        new = [0] * (len(counts) + m - 1)
        for k, c in enumerate(counts):
            for j in range(m):
                new[k + j] += c
        counts = new
    return tuple(counts)


def mann_kendall(xs: list[float], ys: list[float]) -> tuple[int, float]:
    """(S, two-sided p). Exact under the no-ties null: S = N − 2·inversions; ties only shrink |S| (conservative)."""
    n = len(ys)
    s = sum(_sign(xs[j] - xs[i]) * _sign(ys[j] - ys[i]) for i in range(n) for j in range(i + 1, n))
    if n < 2:
        return s, 1.0
    pairs = n * (n - 1) // 2
    # A permutation with k inversions has S = N − 2k.
    tail = sum(c for k, c in enumerate(_kendall_null(n)) if abs(pairs - 2 * k) >= abs(s))
    return s, tail / math.factorial(n)


def trend(points: list[Point], limits: Rcv | None = None, low: float | None = None, high: float | None = None,
          horizon_years: float = HORIZON_YEARS) -> Trend | None:
    """Trend of `points` (any order). None with fewer than MIN_POINTS results or no two distinct dates."""
    pts = sorted(points, key=lambda p: p.when)
    if len(pts) < MIN_POINTS or pts[0].when == pts[-1].when:
        return None
    first, last = pts[0].when, pts[-1].when
    xs = [_years(first, p.when) for p in pts]
    ys = [p.value for p in pts]
    slope, intercept, lo, hi = theil_sen(xs, ys)
    _, p = mann_kendall(xs, ys)

    start, end = intercept, intercept + slope * xs[-1]
    change = end / start - 1 if start > 0 and end > 0 else None
    direction = "flat" if slope == 0 else ("rising" if slope > 0 else "falling")

    if (last - first).days < MIN_SPAN_DAYS:
        reason = "short_span"
    elif p >= ALPHA:
        reason = "too_few" if len(pts) == MIN_POINTS else "not_significant"
    elif limits is None:
        reason = "no_variation_data"
    elif change is None or limits.down <= change <= limits.up:
        reason = "within_variation"
    else:
        reason = ""
    confirmed = reason == "" and direction != "flat"

    result = Trend(len(pts), first, last, slope, intercept, lo, hi, p, change, direction, confirmed, reason, None)
    if confirmed:
        result = replace(result, projection=_project(result, low, high, horizon_years))
    return result


def _project(t: Trend, low: float | None, high: float | None, horizon_years: float) -> Projection | None:
    now = t.fitted(t.last)
    candidates: list[tuple[str, str, float]] = []
    if t.direction == "rising":
        if high is not None and now < high:
            candidates.append(("leave", "high", high))
        if low is not None and now < low:
            candidates.append(("enter", "low", low))
    elif t.direction == "falling":
        if low is not None and now > low:
            candidates.append(("leave", "low", low))
        if high is not None and now > high:
            candidates.append(("enter", "high", high))
    for kind, which, limit in candidates:
        years_from_first = (limit - t.intercept) / t.slope_per_year
        ahead = years_from_first - _years(t.first, t.last)
        if 0 < ahead <= horizon_years:
            return Projection(kind, which, limit, t.first + timedelta(days=round(years_from_first * DAYS_PER_YEAR)))
    return None
