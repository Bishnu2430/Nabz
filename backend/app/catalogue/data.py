"""Read and validate the catalogue CSV files in data/catalogue/."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from app.catalogue.loinc import is_valid_loinc
from app.catalogue.units import normalize_unit

SEXES = {"female", "male", "other", "unknown"}


@dataclass(frozen=True)
class OrganRow:
    code: str
    name_en: str
    name_hi: str
    name_or: str
    mesh_ids: tuple[str, ...]


@dataclass(frozen=True)
class TestRow:
    code: str
    loinc: str
    name: str
    short: str
    panel: str
    organ: str
    unit: str
    decimals: int
    plausible_min: Decimal
    plausible_max: Decimal
    cv_i: float | None
    cv_a: float | None
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class ConversionRow:
    test_code: str
    from_unit: str
    factor: Decimal
    offset: Decimal


@dataclass(frozen=True)
class RangeRow:
    test_code: str
    sex: str
    age_min: int
    age_max: int
    low: Decimal | None
    high: Decimal | None


@dataclass(frozen=True)
class LimitRow:
    test_code: str
    low: Decimal | None
    high: Decimal | None
    message_key: str


@dataclass
class CatalogueData:
    organs: list[OrganRow] = field(default_factory=list)
    tests: list[TestRow] = field(default_factory=list)
    conversions: list[ConversionRow] = field(default_factory=list)
    ranges: list[RangeRow] = field(default_factory=list)
    limits: list[LimitRow] = field(default_factory=list)

    def test(self, code: str) -> TestRow:
        return next(t for t in self.tests if t.code == code)


class CatalogueError(ValueError):
    pass


def _dec(s: str) -> Decimal | None:
    s = s.strip()
    return Decimal(s) if s else None


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def read_catalogue(directory: Path) -> CatalogueData:
    """Parse every CSV and raise CatalogueError listing all problems found."""
    errors: list[str] = []
    data = CatalogueData()

    for r in _rows(directory / "organ_systems.csv"):
        data.organs.append(OrganRow(r["code"], r["name_en"], r["name_hi"], r["name_or"],
                                    tuple(m for m in r["mesh_ids"].split("|") if m)))
    organ_codes = {o.code for o in data.organs}

    for r in _rows(directory / "lab_tests.csv"):
        row = TestRow(
            code=r["code"], loinc=r["loinc"], name=r["name"], short=r["short"], panel=r["panel"],
            organ=r["organ"], unit=r["unit"], decimals=int(r["decimals"]),
            plausible_min=Decimal(r["plausible_min"]), plausible_max=Decimal(r["plausible_max"]),
            cv_i=float(r["cv_i"]) if r["cv_i"] else None, cv_a=float(r["cv_a"]) if r["cv_a"] else None,
            aliases=tuple(a.strip() for a in r["aliases"].split("|") if a.strip()),
        )
        if not is_valid_loinc(row.loinc):
            errors.append(f"{row.code}: invalid LOINC code {row.loinc!r}")
        if row.organ not in organ_codes:
            errors.append(f"{row.code}: unknown organ system {row.organ!r}")
        if row.plausible_min >= row.plausible_max:
            errors.append(f"{row.code}: plausible_min must be below plausible_max")
        if (row.cv_i is None) != (row.cv_a is None):
            errors.append(f"{row.code}: cv_i and cv_a must both be set or both be blank")
        data.tests.append(row)

    codes = [t.code for t in data.tests]
    loincs = [t.loinc for t in data.tests]
    for label, values in (("code", codes), ("LOINC", loincs)):
        dupes = {v for v in values if values.count(v) > 1}
        if dupes:
            errors.append(f"duplicate test {label}s: {sorted(dupes)}")
    known = set(codes)

    for r in _rows(directory / "unit_conversions.csv"):
        row = ConversionRow(r["test_code"], normalize_unit(r["from_unit"]), Decimal(r["factor"]),
                            Decimal(r["offset"] or "0"))
        if row.test_code not in known:
            errors.append(f"conversion for unknown test {row.test_code!r}")
        elif row.from_unit == normalize_unit(data.test(row.test_code).unit):
            errors.append(f"{row.test_code}: conversion from the canonical unit {row.from_unit!r}")
        data.conversions.append(row)

    for r in _rows(directory / "reference_ranges.csv"):
        row = RangeRow(r["test_code"], r["sex"], int(r["age_min"]), int(r["age_max"]), _dec(r["low"]),
                       _dec(r["high"]))
        if row.test_code not in known:
            errors.append(f"range for unknown test {row.test_code!r}")
        if row.sex not in SEXES:
            errors.append(f"{row.test_code}: invalid sex {row.sex!r}")
        if row.low is None and row.high is None:
            errors.append(f"{row.test_code}: range needs a low or a high bound")
        if row.low is not None and row.high is not None and row.low >= row.high:
            errors.append(f"{row.test_code}: range low must be below high")
        data.ranges.append(row)

    for r in _rows(directory / "critical_limits.csv"):
        row = LimitRow(r["test_code"], _dec(r["low"]), _dec(r["high"]), r["message_key"])
        if row.test_code not in known:
            errors.append(f"critical limit for unknown test {row.test_code!r}")
        data.limits.append(row)

    if errors:
        raise CatalogueError("catalogue has problems:\n  " + "\n  ".join(errors))
    return data
