"""Interpret a parsed row: catalogue match, canonical value and range, plausibility, confidence."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from app.catalogue.convert import UnitConverter
from app.catalogue.data import CatalogueData, RangeRow
from app.catalogue.matcher import CatalogueMatcher, Match
from app.catalogue.units import normalize_unit
from app.extraction.parser import parse_range, to_decimal

FEATURES = ("ocr_conf", "text_layer", "match_score", "matched", "unit_ok", "plausible", "has_range",
            "range_excess", "flag_mismatch")


@dataclass(frozen=True)
class RawRow:
    raw_name: str
    raw_value: str
    raw_unit: str | None
    raw_range: str | None
    raw_flag: str | None
    section: str | None
    ocr_conf: float = 1.0
    source: str = "text-layer"  # or "ocr" / "manual"


@dataclass
class Interpreted:
    match: Match
    value_num: Decimal | None = None
    unit: str | None = None  # canonical unit (display form)
    ref_low: Decimal | None = None  # canonical units
    ref_high: Decimal | None = None
    ref_source: str = "none"  # report | catalogue | none
    unit_ok: bool = False
    plausible: bool = False
    features: dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0

    @property
    def test_code(self) -> str | None:
        return self.match.test_code


class ConfidenceModel:
    """Logistic regression over FEATURES → probability that the row was read and mapped correctly.

    Coefficients come from tools/train/confidence.py (data/models/confidence-v1.json). Without a trained
    file, conservative hand-set weights are used.
    """

    DEFAULT = {"intercept": -4.0, "weights": {"ocr_conf": 3.0, "text_layer": 2.0, "match_score": 2.0, "matched": 1.5,
                                              "unit_ok": 1.5, "plausible": 1.5, "has_range": 0.5,
                                              "range_excess": -3.0, "flag_mismatch": -2.5},
               "threshold": 0.8, "version": "default"}

    def __init__(self, params: dict | None = None):
        self.params = params or self.DEFAULT
        self.version = self.params.get("version", "unknown")
        self.threshold = float(self.params.get("threshold", 0.8))

    @classmethod
    def load(cls, path: Path) -> ConfidenceModel:
        return cls(json.loads(path.read_text(encoding="utf-8"))) if path.exists() else cls()

    def predict(self, features: dict[str, float]) -> float:
        z = self.params["intercept"] + sum(w * features.get(k, 0.0) for k, w in self.params["weights"].items())
        return 1 / (1 + math.exp(-max(min(z, 30), -30)))


class Interpreter:
    def __init__(self, catalogue: CatalogueData, matcher: CatalogueMatcher, converter: UnitConverter,
                 model: ConfidenceModel | None = None):
        self.tests = {t.code: t for t in catalogue.tests}
        self.ranges: dict[str, list[RangeRow]] = {}
        for r in catalogue.ranges:
            self.ranges.setdefault(r.test_code, []).append(r)
        self.matcher = matcher
        self.converter = converter
        self.model = model or ConfidenceModel()

    def default_range(self, code: str, sex: str | None, age: int | None) -> RangeRow | None:
        """Catalogue range for this person; None when it depends on sex and the sex is unknown."""
        candidates = [r for r in self.ranges.get(code, []) if age is None or r.age_min <= age <= r.age_max]
        for wanted in ([sex] if sex in ("male", "female") else []) + ["unknown"]:
            for r in candidates:
                if r.sex == wanted:
                    return r
        return None

    def interpret(self, row: RawRow, sex: str | None = None, age: int | None = None,
                  test_code: str | None = None) -> Interpreted:
        """`test_code` forces the mapping (a user's correction); otherwise the matcher decides."""
        match = (Match(test_code, 1.0, "manual") if test_code
                 else self.matcher.match(row.raw_name, row.section, row.raw_unit))
        out = Interpreted(match)
        value = to_decimal(row.raw_value) if row.raw_value else None
        printed = parse_range(row.raw_range) if row.raw_range else None
        code = match.test_code

        if code is not None and value is not None:
            test = self.tests[code]
            unit = row.raw_unit or ""
            unitless = normalize_unit(test.unit) == ""
            out.unit_ok = self.converter.supports(code, unit) and (bool(row.raw_unit) or unitless)
            out.unit = test.unit if test.unit != "ratio" else None
            canonical = self.converter.to_canonical(code, value, unit) if out.unit_ok else None
            out.value_num = canonical if canonical is not None else value
            out.plausible = test.plausible_min <= out.value_num <= test.plausible_max
            if printed is not None and out.unit_ok:
                out.ref_low, out.ref_high = (None if b is None else self.converter.to_canonical(code, b, unit)
                                             for b in printed)
                out.ref_source = "report"
            elif (default := self.default_range(code, sex, age)) is not None:
                out.ref_low, out.ref_high, out.ref_source = default.low, default.high, "catalogue"

        out.features = self._features(row, out, value, printed)
        out.confidence = round(self.model.predict(out.features), 4)
        return out

    @staticmethod
    def _features(row: RawRow, out: Interpreted, value: Decimal | None,
                  printed: tuple[Decimal | None, Decimal | None] | None) -> dict[str, float]:
        excess, mismatch = 0.0, 0.0
        if value is not None and value > 0 and printed is not None:
            lo, hi = printed
            if hi is not None and hi > 0 and value > hi:
                excess = min(math.log10(float(value / hi)), 3.0)
            if lo is not None and lo > 0 and value < lo:
                excess = min(math.log10(float(lo / value)), 3.0)
            outside_high = hi is not None and value > hi
            outside_low = lo is not None and value < lo
            flag = (row.raw_flag or "").upper()
            if (flag == "H" and not outside_high) or (flag == "L" and not outside_low) or \
                    (not flag and (outside_high or outside_low) and excess > 0.3):
                mismatch = 1.0
        return {
            "ocr_conf": float(row.ocr_conf),
            "text_layer": 1.0 if row.source == "text-layer" else 0.0,
            "match_score": float(out.match.score),
            "matched": 1.0 if out.match.test_code else 0.0,
            "unit_ok": 1.0 if out.unit_ok else 0.0,
            "plausible": 1.0 if out.plausible else 0.0,
            "has_range": 1.0 if printed is not None else 0.0,
            "range_excess": excess,
            "flag_mismatch": mismatch,
        }
