"""Pure analysis functions: status, RCV, Theil–Sen + Mann–Kendall trend, percentiles."""

import itertools
import math
import random
from datetime import date, timedelta

import pytest

from app.analysis.change import compare, rcv
from app.analysis.percentile import age_band, place
from app.analysis.status import classify, flag_disagrees, worst
from app.analysis.trend import Point, mann_kendall, theil_sen, trend
from app.models.enums import ObsStatus as S

# --- status (FR-16, FR-17) -------------------------------------------------------------------------------------


@pytest.mark.parametrize(("value", "low", "high", "crit", "expected"), [
    (14.0, 13.0, 17.0, (None, None), S.NORMAL),
    (13.0, 13.0, 17.0, (None, None), S.NORMAL),  # a printed limit is inside the range
    (12.9, 13.0, 17.0, (None, None), S.LOW),
    (17.1, 13.0, 17.0, (None, None), S.HIGH),
    (180, None, 200, (None, None), S.NORMAL),  # "< 200"
    (45, 40, None, (None, None), S.NORMAL),  # "> 40"
    (5.0, None, None, (None, None), S.UNKNOWN),
    (6.5, 3.5, 5.1, (2.8, 6.2), S.CRITICAL_HIGH),  # critical wins over high
    (2.7, 3.5, 5.1, (2.8, 6.2), S.CRITICAL_LOW),
    (6.2, 3.5, 5.1, (2.8, 6.2), S.HIGH),  # equal to the critical limit is not critical
    (6.5, None, None, (2.8, 6.2), S.CRITICAL_HIGH),  # critical applies even with no printed range
    (None, 1, 2, (None, None), S.UNKNOWN),
])
def test_classify(value, low, high, crit, expected) -> None:
    assert classify(value, low, high, *crit) is expected


def test_worst_and_printed_flag() -> None:
    assert worst([S.NORMAL, S.HIGH, S.UNKNOWN]) is S.HIGH
    assert worst([S.LOW, S.CRITICAL_HIGH]) is S.CRITICAL_HIGH
    assert worst([]) is S.UNKNOWN
    assert flag_disagrees(S.NORMAL, "H") and flag_disagrees(S.HIGH, "L")
    assert not flag_disagrees(S.CRITICAL_HIGH, "H") and not flag_disagrees(S.NORMAL, "")


# --- reference change value (FR-18) ----------------------------------------------------------------------------


def test_rcv_is_log_normal_and_asymmetric() -> None:
    limits = rcv(cv_analytical=1.0, cv_within_subject=2.7)  # haemoglobin
    symmetric = 1.96 * math.sqrt(2) * math.hypot(2.7, 1.0) / 100
    assert limits.up == pytest.approx(0.0831, abs=5e-4)
    assert limits.down == pytest.approx(-0.0767, abs=5e-4)
    assert limits.up > symmetric > -limits.down  # a rise must be a little larger than a fall


def test_rcv_needs_within_subject_variation() -> None:
    assert rcv(2.0, None) is None and rcv(None, 0) is None
    assert rcv(None, 10.0).up == pytest.approx(math.expm1(1.96 * math.sqrt(2) * math.sqrt(math.log1p(0.01))))


def test_change_significance() -> None:
    limits = rcv(1.0, 2.7)
    assert compare(14.0, 15.0, limits).significant is False  # +7.1 %
    assert compare(14.0, 15.3, limits).significant is True  # +9.3 %
    assert compare(14.0, 12.8, limits).significant is True  # −8.6 %
    c = compare(14.0, 15.0, None)
    assert c.significant is None and c.direction == "up" and c.fraction == pytest.approx(1 / 14)
    assert compare(0.0, 1.0, limits).fraction is None


# --- Theil–Sen and Mann–Kendall (FR-19) ------------------------------------------------------------------------


@pytest.mark.parametrize("seed", range(8))
def test_theil_sen_matches_scipy(seed: int) -> None:
    stats = pytest.importorskip("scipy.stats")
    rng = random.Random(seed)
    n = rng.randint(4, 12)
    xs = sorted(rng.uniform(0, 6) for _ in range(n))
    ys = [2.0 + 0.4 * x + rng.gauss(0, 0.5) for x in xs]
    if seed % 3 == 0:  # ties in y
        ys[1] = ys[2]
    slope, _, lo, hi = theil_sen(xs, ys, confidence=0.90)
    ref = stats.theilslopes(ys, xs, alpha=0.90)
    assert slope == pytest.approx(ref.slope)
    assert (lo, hi) == (pytest.approx(ref.low_slope), pytest.approx(ref.high_slope))


def _brute_force_p(ys: list[float]) -> float:
    n = len(ys)

    def s_of(seq):
        return sum((seq[j] > seq[i]) - (seq[j] < seq[i]) for i in range(n) for j in range(i + 1, n))

    observed = abs(s_of(ys))
    perms = list(itertools.permutations(ys))
    return sum(abs(s_of(p)) >= observed for p in perms) / len(perms)


@pytest.mark.parametrize("seed", range(5))
def test_mann_kendall_exact_p_matches_permutations(seed: int) -> None:
    rng = random.Random(seed)
    ys = [rng.random() + 0.15 * i for i in range(6)]
    _, p = mann_kendall(list(range(6)), ys)
    assert p == pytest.approx(_brute_force_p(ys))


def test_mann_kendall_small_samples() -> None:
    assert mann_kendall([0, 1, 2], [1, 2, 3]) == (3, pytest.approx(1 / 3))  # three results can never be significant
    assert mann_kendall([0, 1, 2, 3], [1, 2, 3, 4]) == (6, pytest.approx(2 / 24))
    assert mann_kendall([0, 1, 2, 3], [1, 3, 2, 4])[1] > 0.1
    assert mann_kendall([0, 1, 2, 3], [2, 2, 2, 2]) == (0, 1.0)


# --- trend verdicts ---------------------------------------------------------------------------------------------

START = date(2022, 6, 1)


def yearly(values: list[float], start: date = START, step_days: int = 365) -> list[Point]:
    return [Point(start + timedelta(days=step_days * i), v) for i, v in enumerate(values)]


def test_three_results_show_a_direction_but_never_confirm() -> None:
    t = trend(yearly([5.4, 5.8, 6.2]), rcv(1.5, 1.9))
    assert t.direction == "rising" and not t.confirmed and t.reason == "too_few"
    assert t.slope_per_year == pytest.approx(0.4, rel=0.01)


def test_confirmed_rising_hba1c_projects_the_crossing() -> None:
    t = trend(yearly([5.0, 5.3, 5.6, 5.9]), rcv(1.5, 1.9), low=4.0, high=6.5)
    assert t.confirmed and t.reason == "" and t.p_value == pytest.approx(2 / 24)
    assert t.projection.kind == "leave" and t.projection.limit == "high"
    # 0.3 per year from 5.9 reaches 6.5 two years after the last result
    assert abs((t.projection.on - (START + timedelta(days=365 * 3))).days - 2 * 365.25) < 15


def test_projection_back_into_range() -> None:
    t = trend(yearly([190.0, 175.0, 160.0, 145.0, 130.0]), rcv(3.0, 7.0), low=None, high=100.0)
    assert t.confirmed and t.projection.kind == "enter" and t.projection.limit == "high"


def test_no_projection_beyond_the_horizon() -> None:
    t = trend(yearly([100.0, 105.0, 110.0, 115.0, 120.0]), rcv(2.0, 5.0), low=70.0, high=200.0)
    assert t.confirmed and t.projection is None  # 200 is 16 years away at 5 per year


def test_consistent_change_smaller_than_normal_variation_is_not_confirmed() -> None:
    t = trend(yearly([14.0, 14.1, 14.2, 14.3, 14.4]), rcv(1.0, 2.7))
    assert t.p_value < 0.1 and not t.confirmed and t.reason == "within_variation"


def test_short_span_and_degenerate_input() -> None:
    t = trend(yearly([1.0, 2.0, 3.0, 4.0], step_days=30))
    assert not t.confirmed and t.reason == "short_span"
    assert trend(yearly([1.0, 2.0])) is None
    assert trend([Point(START, 1.0), Point(START, 2.0), Point(START, 3.0)]) is None


def test_tests_without_variation_data_show_direction_only() -> None:
    t = trend(yearly([1.0, 2.0, 3.0, 4.0, 5.0]))
    assert t.direction == "rising" and t.p_value < 0.1 and not t.confirmed and t.reason == "no_variation_data"


def test_outlier_does_not_swing_the_slope() -> None:
    t = trend(yearly([100.0, 102.0, 180.0, 106.0, 108.0]))
    assert t.slope_per_year == pytest.approx(2.0, abs=0.5)


# --- percentiles (FR-20) ----------------------------------------------------------------------------------------

CUTS = (10.0, 12.0, 13.0, 14.0, 16.0)


@pytest.mark.parametrize(("value", "percentile", "side"), [
    (9.0, 5, "below"), (10.0, 5, "within"), (12.5, 37.5, "within"), (13.0, 50, "within"),
    (15.0, 85, "within"), (16.0, 95, "within"), (16.1, 95, "above"),
])
def test_place(value, percentile, side) -> None:
    got = place(value, CUTS)
    assert got.percentile == pytest.approx(percentile) and got.side == side


def test_age_bands() -> None:
    assert age_band(18) == (18, 29) and age_band(45) == (40, 49) and age_band(85) == (80, 120)
    assert age_band(12) is None and age_band(None) is None
