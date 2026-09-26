from collections import defaultdict
from pathlib import Path

import pytest

from app.catalogue import CatalogueData, CatalogueError, read_catalogue
from app.catalogue.units import normalize_unit

KNOWN_UNIT_KEYS = {
    "g/dl", "%", "10^6/ul", "10^3/ul", "fl", "pg", "mm/h", "mg/dl", "", "ml/min/1.73m2", "mmol/l", "u/l",
    "uiu/ml", "ng/dl", "pg/ml", "ug/dl", "ng/ml", "mg/l", "/hpf", "mg/g",
}


def test_catalogue_loads(catalogue: CatalogueData) -> None:
    assert len(catalogue.tests) == 70
    assert len(catalogue.organs) == 10


def test_canonical_units_normalise_to_known_keys(catalogue: CatalogueData) -> None:
    for t in catalogue.tests:
        assert normalize_unit(t.unit) in KNOWN_UNIT_KEYS, t.code


def test_every_test_has_a_default_range(catalogue: CatalogueData) -> None:
    with_ranges = {r.test_code for r in catalogue.ranges}
    missing = [t.code for t in catalogue.tests if t.code not in with_ranges]
    assert missing == []


def test_aliases_are_unambiguous_within_a_panel(catalogue: CatalogueData) -> None:
    seen: dict[tuple[str, str], str] = {}
    clashes = []
    for t in catalogue.tests:
        for alias in (*t.aliases, t.name):
            key = (t.panel, alias.casefold())
            if key in seen and seen[key] != t.code:
                clashes.append((alias, seen[key], t.code))
            seen[key] = t.code
    assert clashes == []


def test_critical_limits_lie_outside_reference_ranges(catalogue: CatalogueData) -> None:
    ranges = defaultdict(list)
    for r in catalogue.ranges:
        ranges[r.test_code].append(r)
    for lim in catalogue.limits:
        for r in ranges[lim.test_code]:
            if lim.low is not None and r.low is not None:
                assert lim.low < r.low, lim.test_code
            if lim.high is not None and r.high is not None:
                assert lim.high > r.high, lim.test_code


def test_reference_ranges_lie_within_plausible_bounds(catalogue: CatalogueData) -> None:
    for r in catalogue.ranges:
        t = catalogue.test(r.test_code)
        for bound in (r.low, r.high):
            if bound is not None:
                assert t.plausible_min <= bound <= t.plausible_max, r


def test_invalid_loinc_is_reported(catalogue_dir: Path, tmp_path: Path) -> None:
    for f in catalogue_dir.glob("*.csv"):
        (tmp_path / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    tests = tmp_path / "lab_tests.csv"
    tests.write_text(tests.read_text(encoding="utf-8").replace(",718-7,", ",718-8,"), encoding="utf-8")
    with pytest.raises(CatalogueError, match="invalid LOINC"):
        read_catalogue(tmp_path)
